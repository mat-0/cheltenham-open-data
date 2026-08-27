---
layout: page
title: "Welcome to Cheltenham Open Data"
seo: "Cheltenham, Gloucestershire, UK. Local news, cheapest fuel prices, weather, street issues helpful phone numbers and more."
permalink: /
type: welcome
description: "Collecting and sharing frequently updated local open data for Cheltenham and Gloucestershire — weather, fuel prices, flood warnings, market dates, food banks, news and more."
---

<!-- weather_marker starts -->
## On Thursday, 27 August 2026

- The average temperature today is 22.68˚C,
- With highs of 24.03˚C and lows of 21.37˚C,
- It may feel like 22.88˚C with overcast clouds
- The wind speed is 2.68m/s and visibility is 10000m
- The pressure is 1006hPa and humidity is 72%
- The sun will rise at 05:12 and set at 19:08

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
