---
layout: page
title: "Welcome to Cheltenham Open Data"
seo: "Cheltenham, Gloucestershire, UK. Local news, cheapest fuel prices, weather, street issues helpful phone numbers and more."
permalink: /
type: welcome
description: "Collecting and sharing frequently updated local open data for Cheltenham and Gloucestershire — weather, fuel prices, flood warnings, market dates, food banks, news and more."
---

<!-- weather_marker starts -->
## On Sunday, 23 August 2026

- The average temperature today is 14.54˚C,
- With highs of 15.95˚C and lows of 14.27˚C,
- It may feel like 13.67˚C with clear sky
- The wind speed is 0.45m/s and visibility is 10000m
- The pressure is 1023hPa and humidity is 62%
- The sun will rise at 05:05 and set at 19:16

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

## Sponsors & Offers

- [Get £50 credit when switching to Octopus Energy](https://bit.ly/3oD1nnS)
- [Get up to £100 cashback when taking a YouFibre broadband plan with code 5QGYSF](https://youfibre.com)
- [Get £5 free credit when you join the Electroverse](https://electroverse.octopus.energy/sign-up/magic?referralCode=aglow-louse-16571)
- [Get a £25 Visa card when you install an EV charger with Octopus](https://tech.referrals.octopus.energy/ulLGI6SC)
- [Choose a gift card up to £20 when you join Smarty Mobile](https://i.smarty.co.uk/CSj6iK)
- [Get £20, £50 or £100 free when you join Monzo bank](https://join.monzo.com/c/k7stxxwv)

Note: _Terms and Conditions apply - see offer for details_.
