---
layout: page
title: "Local open data for Cheltenham & Gloucestershire"
seo_title: "Cheltenham Fuel Prices, House Prices, Crime & News"
seo: "Free Cheltenham open data for Gloucestershire: compare local fuel prices, check crime stats, house prices, flood warnings, food banks, GPs, planning and news."
permalink: /
type: "cod"
description: "The open data hub for Cheltenham and Gloucestershire. Fuel prices, crime figures, flood alerts, food banks, GPs, planning and local news — all free, in one place."
---

<!-- weather_marker starts -->
## On Monday, 07 September 2026

- The average temperature today is 17.64˚C,
- With highs of 18.43˚C and lows of 17.05˚C,
- It may feel like 17.84˚C with broken clouds
- The wind speed is 4.47m/s and visibility is 10000m
- The pressure is 1014hPa and humidity is 91%
- The sun will rise at 05:29 and set at 18:43

<!-- weather_marker ends -->
[See the full 16-day Cheltenham forecast &rarr;](/cheltenahm-10-day-weather-forecast)

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

### Cheltenham Racing Festival

- [Starting 16th March 2027](https://www.thejockeyclub.co.uk/cheltenham-festival/) &rarr;

### Cheltenham Jazz Festival

- [Starting 28th April 2027](https://www.cheltenhamfestivals.org/festivals/jazz-festival) &rarr;

### Cheltenham Science Festival

- [Starting 8th June 2027](https://www.cheltenhamfestivals.org/festivals/science-festival) &rarr;

### Cheltenham Music Festival

- [Starting 9th July 2027](https://www.cheltenhamfestivals.org/festivals/music-festival) &rarr;
