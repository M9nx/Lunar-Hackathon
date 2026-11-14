/**
 * Offline Three.js scene for the review candidate.
 * Illustrative lighting and pins only — not SPICE, not terrain clearance.
 */
import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const globe = {
  ready: false,
  followStream: true,
  view: "3d",
};

function loadTexture(url, colorSpace) {
  return new Promise((resolve, reject) => {
    const loader = new THREE.TextureLoader();
    loader.load(
      url,
      (texture) => {
        texture.anisotropy = 8;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        if (colorSpace && THREE.SRGBColorSpace) texture.colorSpace = colorSpace;
        resolve(texture);
      },
      undefined,
      reject,
    );
  });
}

function fallbackColorTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#9a9084";
  ctx.fillRect(0, 0, 512, 256);
  for (let i = 0; i < 180; i += 1) {
    ctx.fillStyle = `rgba(40,36,32,${0.08 + Math.random() * 0.2})`;
    ctx.beginPath();
    ctx.arc(Math.random() * 512, Math.random() * 256, 2 + Math.random() * 14, 0, Math.PI * 2);
    ctx.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

async function loadMoonMaps() {
  try {
    const [color, bump] = await Promise.all([
      loadTexture("./media/lroc_color_2k.jpg", THREE.SRGBColorSpace),
      loadTexture("./media/ldem_4ppd_preview.jpg", null),
    ]);
    return { color, bump };
  } catch (_error) {
    return { color: fallbackColorTexture(), bump: null };
  }
}

function earthTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#1b4f8c";
  ctx.fillRect(0, 0, 128, 64);
  ctx.fillStyle = "#2f8f56";
  [
    [18, 22, 28, 16],
    [52, 18, 22, 14],
    [88, 28, 26, 12],
    [30, 40, 18, 10],
  ].forEach(([x, y, w, h]) => {
    ctx.beginPath();
    ctx.ellipse(x, y, w / 2, h / 2, 0.2, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.fillStyle = "#e8eef4";
  ctx.fillRect(0, 0, 128, 6);
  ctx.fillRect(0, 58, 128, 6);
  const texture = new THREE.CanvasTexture(canvas);
  if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function latLonToVec(lat, lon, radius) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function makeBeacon(color) {
  const group = new THREE.Group();
  const cone = new THREE.Mesh(
    new THREE.ConeGeometry(0.03, 0.11, 12),
    new THREE.MeshBasicMaterial({ color }),
  );
  cone.position.y = 0.07;
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(0.042, 0.008, 8, 20),
    new THREE.MeshBasicMaterial({ color }),
  );
  ring.rotation.x = Math.PI / 2;
  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(0.035, 12, 12),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.35 }),
  );
  glow.position.y = 0.02;
  group.add(cone, ring, glow);
  group.userData.glow = glow;
  group.userData.baseColor = color;
  return group;
}

function placeBeacon(group, lat, lon) {
  const point = latLonToVec(lat, lon, 1.02);
  group.position.copy(point);
  group.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), point.clone().normalize());
}

function directionFromAzEl(azimuthDeg, elevationDeg, radius) {
  const az = (Number(azimuthDeg) * Math.PI) / 180;
  const el = (Number(elevationDeg) * Math.PI) / 180;
  return new THREE.Vector3(
    Math.cos(el) * Math.sin(az),
    Math.sin(el),
    Math.cos(el) * Math.cos(az),
  ).normalize().multiplyScalar(radius);
}

function stateColor(state) {
  if (state === "clear") return 0x3ea072;
  if (state === "blocked") return 0xc9a15b;
  if (state === "unknown") return 0xc4b5fd;
  return 0x8d8d92;
}

function setHud(samples, selectedSite) {
  const hud = document.getElementById("scene-hud");
  if (!hud) return;
  const sample = samples?.[selectedSite] || samples?.[0] || null;
  const bodies = [
    ["sun", "Sun"],
    ["earth", "Earth"],
    ["both", "Both"],
  ];
  bodies.forEach(([key, label]) => {
    const node = hud.querySelector(`[data-body="${key}"]`);
    if (!node) return;
    if (!sample || !sample[key]) {
      node.textContent = `${label} · pending`;
      node.dataset.state = "pending";
      return;
    }
    const item = sample[key];
    const elev = item.elevation_deg == null ? "null" : `${item.elevation_deg}°`;
    node.textContent = `${label} · ${item.state} · elev ${elev}`;
    node.dataset.state = item.state;
  });
}

function setView(view) {
  globe.view = view;
  const map = document.getElementById("context-map");
  const threeHost = document.getElementById("scene-3d");
  const buttons = document.querySelectorAll("[data-scene-view]");
  buttons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.sceneView === view));
  });
  if (view === "3d") {
    if (map) map.hidden = true;
    if (threeHost) {
      threeHost.hidden = false;
      threeHost.setAttribute("aria-hidden", "false");
    }
    resize();
  } else {
    if (threeHost) {
      threeHost.hidden = true;
      threeHost.setAttribute("aria-hidden", "true");
    }
    if (map) map.hidden = false;
  }
}

function resize() {
  if (!globe.ready) return;
  const host = globe.host;
  const width = host.clientWidth || 320;
  const height = host.clientHeight || 320;
  globe.camera.aspect = width / height;
  globe.camera.updateProjectionMatrix();
  globe.renderer.setSize(width, height, false);
}

function updateScene(detail = {}) {
  if (!globe.ready) {
    setHud(detail.samples, detail.selectedSite || 0);
    return;
  }
  const sites = detail.sites || [];
  if (sites[0]) placeBeacon(globe.pinA, sites[0].latitude_deg, sites[0].longitude_east_deg);
  if (sites[1]) placeBeacon(globe.pinB, sites[1].latitude_deg, sites[1].longitude_east_deg);
  else globe.pinB.visible = sites.length > 1;
  globe.pinB.visible = sites.length > 1;

  const selected = detail.selectedSite || 0;
  globe.pinA.scale.setScalar(selected === 0 ? 1.35 : 1);
  globe.pinB.scale.setScalar(selected === 1 ? 1.35 : 1);

  const samples = detail.samples || [];
  const sample = samples[selected] || samples[0];
  if (sample?.sun && typeof sample.sun.azimuth_deg === "number" && typeof sample.sun.elevation_deg === "number") {
    const sunPos = directionFromAzEl(sample.sun.azimuth_deg, sample.sun.elevation_deg, 4.4);
    globe.sun.position.copy(sunPos);
    globe.sunBall.position.copy(sunPos);
    globe.sun.intensity = sample.sun.state === "clear" ? 1.55 : sample.sun.state === "blocked" ? 0.55 : 0.85;
    globe.sunBall.material.color.setHex(stateColor(sample.sun.state));
  }
  if (sample?.earth && typeof sample.earth.azimuth_deg === "number" && typeof sample.earth.elevation_deg === "number") {
    globe.earth.position.copy(directionFromAzEl(sample.earth.azimuth_deg, sample.earth.elevation_deg, 2.15));
    globe.earth.material.opacity = sample.earth.state === "unknown" ? 0.45 : 1;
  }

  const pulse = sample?.sun?.state === "clear" && !reducedMotion ? 0.45 + 0.25 * Math.sin(performance.now() / 280) : 0.3;
  if (globe.pinA.userData.glow) globe.pinA.userData.glow.material.opacity = selected === 0 ? pulse : 0.22;
  if (globe.pinB.userData.glow) globe.pinB.userData.glow.material.opacity = selected === 1 ? pulse : 0.22;

  if (detail.live && detail.partial && globe.followStream && !reducedMotion) {
    const target = selected === 1 ? globe.pinB.position : globe.pinA.position;
    globe.controls.target.lerp(target.clone().multiplyScalar(0.35), 0.08);
  }

  const caption = document.getElementById("context-caption");
  if (caption && sample) {
    const utc = sample.timestamp_utc || "—";
    caption.textContent = `Illustrative 3D · ${utc} · Sun ${sample.sun?.state || "—"} · Earth ${sample.earth?.state || "—"} · not SPICE · terrain Unknown`;
  }
  setHud(samples, selected);

  const note = document.getElementById("scene-stream-note");
  if (note) {
    if (detail.live && detail.partial) note.textContent = "Following stream batches. Drag to orbit. Pins stay tied to the shared playhead.";
    else if (detail.live) note.textContent = "Stream complete. Scene still tracks the shared playhead.";
    else note.textContent = "Scene tracks the shared UTC playhead. Drag to orbit. Map view keeps the PIA context.";
  }
}

async function initGlobe() {
  const host = document.getElementById("scene-3d");
  const stage = document.getElementById("scene-stage");
  if (!host || !stage) return;
  try {
    host.innerHTML = '<p class="scene-loading">Loading LROC color mosaic…</p>';
    const maps = await loadMoonMaps();
    const width = host.clientWidth || 320;
    const height = host.clientHeight || 320;
    const scene = new THREE.Scene();
    scene.background = null;
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 50);
    // Moon Trek-like south-polar approach (fill the stage)
    camera.position.set(0.08, -2.35, 1.55);
    camera.lookAt(0, -0.72, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace || renderer.outputColorSpace;
    host.innerHTML = "";
    host.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, -0.72, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 1.45;
    controls.maxDistance = 6.5;
    controls.enablePan = false;
    controls.maxPolarAngle = Math.PI * 0.95;

    const moonMat = new THREE.MeshStandardMaterial({
      map: maps.color,
      bumpMap: maps.bump || undefined,
      bumpScale: maps.bump ? 0.042 : 0,
      roughness: 0.94,
      metalness: 0.02,
      color: 0xffffff,
    });
    const moon = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 128), moonMat);
    scene.add(moon);

    // Soft limb glow (Trek-ish atmosphere cue; cosmetic only)
    const glow = new THREE.Mesh(
      new THREE.SphereGeometry(1.04, 64, 64),
      new THREE.MeshBasicMaterial({
        color: 0xa8bdd4,
        transparent: true,
        opacity: 0.09,
        side: THREE.BackSide,
      }),
    );
    scene.add(glow);

    // Sparse starfield (local point cloud only)
    const starCount = 420;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i += 1) {
      const r = 12 + Math.random() * 18;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      starPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      starPos[i * 3 + 2] = r * Math.cos(phi);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
    scene.add(new THREE.Points(
      starGeo,
      new THREE.PointsMaterial({ color: 0xd7e3f2, size: 0.035, sizeAttenuation: true, transparent: true, opacity: 0.75 }),
    ));

    function addLatRing(latDeg, color, opacity, width = 1) {
      const pts = [];
      const lat = (latDeg * Math.PI) / 180;
      const y = Math.sin(lat);
      const r = Math.cos(lat) * 1.002;
      for (let i = 0; i <= 96; i += 1) {
        const t = (i / 96) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(t) * r, y, Math.sin(t) * r));
      }
      moon.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color, transparent: true, opacity, linewidth: width }),
      ));
    }

    function addMeridian(lonDeg, color, opacity) {
      const pts = [];
      const lon = (lonDeg * Math.PI) / 180;
      for (let i = 0; i <= 64; i += 1) {
        const lat = (-Math.PI / 2) + (i / 64) * Math.PI;
        const y = Math.sin(lat);
        const r = Math.cos(lat) * 1.002;
        pts.push(new THREE.Vector3(Math.cos(lon) * r, y, Math.sin(lon) * r));
      }
      moon.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color, transparent: true, opacity }),
      ));
    }

    // Trek-like overlay grid (cosmetic; not a DEM product)
    [-60, -30, 0, 30, 60].forEach((lat) => {
      addLatRing(lat, lat === 0 ? 0x8aa4bd : 0x4d5d72, lat === 0 ? 0.38 : 0.18);
    });
    [0, 45, 90, 135, 180, 225, 270, 315].forEach((lon) => addMeridian(lon, 0x4d5d72, 0.14));

    const polePts = [];
    for (let i = 0; i <= 72; i += 1) {
      const t = (i / 72) * Math.PI * 2;
      polePts.push(new THREE.Vector3(Math.cos(t) * 0.16, -0.987, Math.sin(t) * 0.16));
    }
    moon.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(polePts),
      new THREE.LineBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.9 }),
    ));

    const amb = new THREE.AmbientLight(0x8a96a8, 0.34);
    const fill = new THREE.HemisphereLight(0xd0dcec, 0x1a1510, 0.48);
    const sun = new THREE.DirectionalLight(0xfff4e0, 2.05);
    sun.position.set(3.5, 1.2, 2.2);
    const sunBall = new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 20, 20),
      new THREE.MeshBasicMaterial({ color: 0xffe08a }),
    );
    const earth = new THREE.Mesh(
      new THREE.SphereGeometry(0.11, 24, 24),
      new THREE.MeshBasicMaterial({ map: earthTexture(), transparent: true }),
    );
    const pinA = makeBeacon(0xe3b34a);
    const pinB = makeBeacon(0x5ba8d8);
    moon.add(pinA, pinB);
    scene.add(amb, fill, sun, sunBall, earth);

    Object.assign(globe, {
      ready: true,
      host,
      scene,
      camera,
      renderer,
      controls,
      moon,
      sun,
      sunBall,
      earth,
      pinA,
      pinB,
    });

    window.addEventListener("resize", resize);
    function tick() {
      controls.update();
      renderer.render(scene, camera);
      globe.raf = requestAnimationFrame(tick);
    }
    tick();
    setView("3d");
    document.dispatchEvent(new CustomEvent("lunar:scene-module-ready", { detail: { ready: true } }));
  } catch (error) {
    host.hidden = false;
    host.textContent = "3D scene unavailable. Map view still works.";
    globe.ready = false;
    setView("map");
    document.dispatchEvent(new CustomEvent("lunar:scene-module-ready", { detail: { ready: false } }));
  }
}

function bindSceneChrome() {
  document.querySelectorAll("[data-scene-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.sceneView));
  });
  const follow = document.getElementById("follow-stream");
  if (follow) {
    follow.checked = true;
    follow.addEventListener("change", () => {
      globe.followStream = follow.checked;
    });
  }
  const stage = document.getElementById("scene-stage");
  if (!stage) return;
  stage.addEventListener("lunar:scene-updated", (event) => updateScene(event.detail || {}));
  stage.addEventListener("lunar:stream-batch", (event) => {
    updateScene({ ...(event.detail || {}), live: true, partial: true });
  });
  stage.addEventListener("lunar:stream-complete", (event) => {
    updateScene({ ...(event.detail || {}), live: true, partial: false });
  });
}

bindSceneChrome();
window.LunarScene = { update: updateScene, setView, ready: () => globe.ready };
initGlobe();
