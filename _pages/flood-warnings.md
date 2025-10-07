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
-  A flood alert has been issued due to a period of high tides. Tides will be at their highest around 20:15 this evening 07/10/25 and between 08:30 and 08:45 on Wednesday 08/10/25. Flooding to roads and low-lying land adjacent the Wye Estuary from Redbrook to Chepstow is expected at the time of high tides, however conditions may apply a few hours either side of the high tides. Predicted peaks at Newport 7.1m to 7.3m and Avonmouth 7.5m to 7.7m around 20:15 this evening Tuesday 07/10/25. Wednesday morning tide peaks Newport 6.9m to 7.2m and Avonmouth 7.4m to 7.6m. We are closely monitoring the situation. Please avoid using low lying footpaths near local watercourses. This message will be updated by 11:00 on 08/10/25, or as the situation changes.

<!-- flood_marker ends -->