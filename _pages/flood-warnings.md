---

layout: page
title: Flood Warnings Feed
seo: flood warnings in Cheltenham
permalink: /flood-warnings

---

This project fetches flood warning data for the Gloucestershire area and publishes it as an [RSS feed](/flood.xml).

## Setup

1. Configure GitHub action runs on a schedule and choose your location
2. Action saves data as`data.json`
3. Python script executed in the action converts `flood.json` to `flood.xml`
4. Published using a GitHub Pages the RSS feed is available.

## Latest

<!-- flood_marker starts -->
- Flood alert: Wye Estuary in Gloucestershire
- A flood alert has been issued as a result of an upcoming period of high tides. Tides will be at their highest between 20:45 today, 08/09/25 and 21:45 Wednesday, 10/09/25. Flooding to roads and low lying land adjacent the Wye Estuary from Redbrook to Chepstow is expected at the times of high tides, however conditions may apply a few hours either side of the high tides.
Predicted peaks at Newport 7.2m at 20:45 on 08/09 and 7.1m at 09:00 on 09/09.  
We are closely monitoring the situation.
Please avoid using low lying footpaths near local watercourses.  
This message will be updated by 13:00 on 09/09/25, or as the situation changes.

<!-- flood_marker ends -->