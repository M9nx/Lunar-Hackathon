# Demo walkthrough (about three minutes)

Practice inputs, centre-ray, terrain Unknown. Say that at the start. Start the page with the command in the [User Guide](../user-guide.md) and open `/review-candidate/`.

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | Show the headline on *Practice replay*. | "Two lunar south-pole sites, 48 hours of saved NASA/JPL Horizons data. Site04 had the Sun's centre above the 0° horizon the whole time. Malapert never did. Neither site had the Sun and Earth centres clear together." |
| 0:30 | Drag the playhead. Point at the two sky plots and the timeline. | "Both sites at the same UTC time. Solid ring is clear, dashed is blocked. This is the centre of the body against a flat 0° horizon. It is not disc visibility, power, or a ground-station link." |
| 1:00 | Click **Why Malapert 0 h?** | "Every number traces to a saved row: the Horizons line, the elevation, the horizon, the margin. At best the Sun's centre was 1.6° below the horizon. Zero or less counts as blocked." |
| 1:30 | Click **Why terrain Unknown?** | "Terrain is not reviewed, so the tool does not guess. It shows the 0° baseline and says terrain is Unknown." |
| 1:50 | In *Is there a clear window?* choose *Sun-centre clearance*, *4 h or longer*. | "Site04 has one window. Malapert has none; here is its closest sample." |
| 2:15 | Click **Practice, 30 days**. Pick the first window of each site. | "A second practice input, where states change. Malapert's Sun centre is clear from 5 January 10:00 to 23 January 14:00 UTC: 436 hours. The rule and the row at each edge are one click away." |
| 2:45 | Under *Or calculate live* pick the practice pair, press **Start stream** for the practice pair, show the totals match. | "Computed again from the same saved files, offline. The totals match the saved results." |
| 3:00 | Close. | "Practice data, centre-ray only, terrain Unknown, eligibility pending the Lead." |

Do not say: the Sun is visible, power is available, a station can talk to Earth, or the result is eligible for submission.

If something fails: reload the page; if **Start stream** fails, restart the server (Operator Manual §3, §8). Saved cases work with the file-only server.
