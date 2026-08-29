---
layout: page
title: "Welcome to Cheltenham Open Data"
seo: "Cheltenham, Gloucestershire, UK. Local news, cheapest fuel prices, weather, street issues helpful phone numbers and more."
permalink: /
type: welcome
description: "Collecting and sharing frequently updated local open data for Cheltenham and Gloucestershire — weather, fuel prices, flood warnings, market dates, food banks, news and more."
---

<!-- weather_marker starts -->
## On Saturday, 29 August 2026

- The average temperature today is 16.34˚C,
- With highs of 16.65˚C and lows of 15.93˚C,
- It may feel like 16.41˚C with light rain
- The wind speed is 2.24m/s and visibility is 10000m
- The pressure is 1005hPa and humidity is 91%
- The sun will rise at 05:15 and set at 19:03

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
