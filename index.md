---
layout: page
title: "Welcome to Cheltenham Open Data"
seo: "Cheltenham, Gloucestershire, UK. Local news, cheapest fuel prices, weather, street issues helpful phone numbers and more."
permalink: /
type: "cod"
description: "Collecting and sharing frequently updated local open data for Cheltenham and Gloucestershire — weather, fuel prices, flood warnings, market dates, food banks, news and more."
---

<!-- weather_marker starts -->
## On Saturday, 05 September 2026

- The average temperature today is 13.19˚C,
- With highs of 14.45˚C and lows of 12.14˚C,
- It may feel like 12.78˚C with clear sky
- The wind speed is 1.79m/s and visibility is 10000m
- The pressure is 1019hPa and humidity is 85%
- The sun will rise at 05:26 and set at 18:48

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

## Upcoming Festivals

### Cheltenham Literature Festival

- [Starting 9th October 2026](https://www.cheltenhamfestivals.org/festivals/literature-festival) &rarr;

### Cheltenham Jazz Festival

- [Starting 28th April 2027](https://www.cheltenhamfestivals.org/festivals/jazz-festival) &rarr;

### Cheltenham Science Festival

- [Starting 8th June 2027](https://www.cheltenhamfestivals.org/festivals/science-festival) &rarr;

### Cheltenham Music Festival

- [Starting 9th July 2027](https://www.cheltenhamfestivals.org/festivals/music-festival) &rarr;
