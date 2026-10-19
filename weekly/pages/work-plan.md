# Work plan

Where the project is and what comes next. The idea: the site publishes everything **automatically first**, and each page is then
**reviewed and improved by hand**; comments from other users go in the box at the bottom of every page.

## Weekly routine

| When | What | Who |
|---|---|---|
| Every morning, 06:40 UTC | the GitHub Action collects finished LBA games, fetches the EuroCup data, regenerates what changed and rebuilds the site | automatic |
| Before each game | open the next games on the home page; read the opponent analysis and the BC Roma snapshot; write key points, comparison and what to expect in the notes; set `reviewed: yes` | analyst |
| When asked | read the comments left on the pages and answer, or fold them into the text | analyst |


## Next steps and ideas

1. **Fetch data from Synergy and/or Instat via API** Check if it's possible to have access granted to the API's endpoints
2. **Player health status and performance** Triangulate performance, work-load and health status data. 
3. **Player subpages** with the history of each player's numbers and minutes.
4. **Playing philosophy**. Definition of quantitative metrics reflecting the playing philosophy of the club and the tactical decisions.
Metrics to be tracked to measure player adherence to the philosophy and philosophy effectiveness.
5. **Live tagging console** Improve live tagging of the games.
6. **Alerts definition** Define alerts based on specific metrics of interest (significant "increasing" or "decreasing" playing time, efficiency, etc.) for BC Roma team and opponents.

Suggestions and corrections are welcome as comments on any page.
