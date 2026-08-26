---
layout: page
title: "Welcome to Cheltenham Open Data"
seo: "Cheltenham, Gloucestershire, UK. Local news, cheapest fuel prices, weather, street issues helpful phone numbers and more."
permalink: /
type: welcome
description: "Collecting and sharing frequently updated local open data for Cheltenham and Gloucestershire — weather, fuel prices, flood warnings, market dates, food banks, news and more."
---

<!-- weather_marker starts -->
## On Wednesday, 26 August 2026

- The average temperature today is 16.93˚C,
- With highs of 17.65˚C and lows of 16.49˚C,
- It may feel like 16.77˚C with overcast clouds
- The wind speed is 1.79m/s and visibility is 10000m
- The pressure is 1011hPa and humidity is 80%
- The sun will rise at 05:10 and set at 19:10

<!-- weather_marker ends -->

## Local Classifieds in Cheltenham

{% assign now = site.time | date: "%s" | plus: 0 %}
{% assign count = 0 %}
{% for item in site.classifieds %}
  {% assign exp = item.expires | date: "%s" | plus: 0 %}
  {% if exp > now %}
    {% assign count = count | plus: 1 %}
  {% endif %}
{% endfor %}

- [Currently there are {{ count }} live classifieds](/cheltenham-classifieds)
- [Add yours](/submission)

{% include referral.html %}

## Sponsorships Available

{% include sponsor.html sponsor=page.sponsor %}
