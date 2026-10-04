---
type: project
match: pollywog-scheduling-automation
summary: A Microsoft Access system that turned a transportation broker's daily trip lists into driver schedules automatically, cutting nightly scheduling prep from about four hours to about thirty minutes.
role: Sole developer
stack: Microsoft Access, VBA, SQL
year: 2011–2017
result_headline: Nightly prep cut from about 4 hours to about 30 minutes; auto-placement accuracy rose from 75% to 93%.
seo_title: Pollywog: driver scheduling automation in Microsoft Access | Jeremy Guill
seo_description: How I built Pollywog, a Microsoft Access and VBA system that turned a non-emergency transportation broker's trip lists into optimized driver schedules, cutting nightly prep from four hours to thirty minutes and recovering unpaid trip revenue.
---
## The Problem

Before Pollywog, building the nightly driver schedule was entirely manual. The trips came in from a non-emergency transportation broker. The dispatcher then took the private rides that had already been scheduled on paper sheets and added the broker's trips to those sheets, one trip at a time.

If a ride needed to move to a different driver, he whited out the entry and rewrote it in another column. When the sheets looked right, he still had to text each driver their first and second trip of the day before he could go home.

That process took a lot of time, and it took a mental toll after an 8 to 12 hour workday.

## What I Built

Around 2011 I asked my boss if I could start working on something to make scheduling easier. I was the only developer, and I had no idea what it would turn into. It developed into a great tool.

Pollywog is a Microsoft Access application built with VBA and SQL queries. I also built the forms and reports to match the ones the office already used. We wanted to keep some consistency while we updated the system, so nobody had to relearn everything at once.

<!-- SCREENSHOT PLACEHOLDER: Pollywog main screen or a schedule form (owner to supply; remove any rider names) -->

## How It Works

Each night the dispatcher downloaded the broker's trip file and Pollywog took it from there:

1. **Import.** Pollywog loaded every trip from the CSV file into a table.
2. **Sort.** It sorted the trips by zip code.
3. **Schedule.** Working through each zip code list by pickup time, it placed trips on schedules based on drive time, deadhead miles (miles driven without a passenger) and the time already on each schedule. Two 8:00 pickups meant two separate schedules.
4. **Pair the returns.** If a trip's return was still waiting in the queue, Pollywog put it on the same schedule.
5. **Check for a better fit.** Before sending a schedule across town, it looked over the other schedules for a closer match in the same zip code, so it optimized as much as it could.
6. **Hand off the exceptions.** Any trip it could not place went onto an unscheduled schedule for the dispatcher to assign by hand.
7. **Review and send.** We printed the schedules and the dispatcher looked them over. When he was happy, he pressed a button and Pollywog sent every schedule out to the drivers.

<!-- SCREENSHOT PLACEHOLDER: an example schedule report (owner to supply; remove any rider names) -->

## The Hard Parts

The two things I am proudest of were also the hardest.

- **Matching trips to time slots.** Working out how to make the computer assign each trip to the right time slot was very tricky, and it felt great when it finally worked.
- **Sorting and dividing the trips into schedules.** This was the largest part of the project by far.

Underneath both of those, I was learning Microsoft Access while building a complex, dynamic system. I would come home and watch YouTube videos to work out how to do something in Access, search for code snippets, find a different way to implement an idea, or scrap it and start over.

## The Result

The time savings came from replacing a long manual routine with a short one:

| Before | After |
| --- | --- |
| Write each trip onto the sheets by hand | Download the trip file |
| Move trips between drivers with whiteout | Press a button |
| Text every driver their first and second trip | Print, verify and email the schedules |

- **Time:** Nightly scheduling prep dropped from about four hours to about thirty minutes.
- **Accuracy:** At first, Pollywog placed about 75% of trips correctly, so out of 100 trips we had to move about 25. I kept working on the algorithm for more than a year. By the end it placed about 93% correctly, and we only had to move about 7 trips out of 100.
- **Billing:** We had not planned for this one. Because every trip now lived in one database instead of the old manual process, we found that the broker had been shorting us each month. We recovered a few thousand dollars in unpaid trips.
- **Longevity:** Pollywog stayed in use for about two to three years after I left the company.

## What I Learned

If I did it again and could choose the tool, I would research other languages and learn something like Python instead of learning Microsoft Access.

That is the path I took next. After Pollywog I learned Python, and I use it extensively today, as projects like [Dudefish Printing OS](/work/dfp-os) show.

If Access was all I had, I would document far more as I went. I would write down my thinking while I was working, instead of trying to work out what I had been doing when I came back to a part of the project later.
