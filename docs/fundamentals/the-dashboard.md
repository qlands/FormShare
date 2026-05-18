---
description: The dashboard is your starting point in FormShare — it shows the activity, forms, and team of your active project at a glance.
---

# The dashboard

The dashboard is the home page of a FormShare account. It always shows your **active project** — the one project (out of those you own or collaborate on) that you have marked as active with the ⭐ icon. From here you can review forms, check submission progress, see who is on the team, and jump into any other project.

> Add screenshot of the dashboard with each numbered area called out here.

1. **Active project**: The dashboard always reflects your active project. The project name appears at the top, along with the icon and color you chose when creating it.
2. **Forms**: A grid of the forms inside the active project, each shown with its color, status (active or inactive), and submission count. Use the **Add new form** button to upload a new form straight into the active project, bypassing the project details page.
3. **Map**: A map plotting all submissions across all forms in the active project. Each point is colored to match its form, so you can quickly tell which form a submission belongs to. The map only includes submissions whose form has a geopoint variable outside any repeat — see "[How does FormShare stores my data?](repositories/how-does-formshare-stores-my-data.md)" for the details.
4. **Collaborations**: A list of projects you collaborate on (projects owned by other FormShare users who added you as a [collaborator](members.md)). Click a collaboration to switch into that project.
5. **Projects**: Your own projects. Use the **Create a new project** button to add a project, and the **Set as active** button next to any project in the list to change which project the dashboard tracks.

## Activity and statistics

The dashboard surfaces a few headline numbers about the active project so you don't have to dig into each form:

* **Total submissions** received across all forms in the project.
* **Last submission** date and time, plus the assistant who sent it. This is useful for spotting projects where data collection has stalled.
* **Forms** split into active (accepting submissions) and inactive.
* **Number of forms with GPS data** — these are the forms that contribute to the map.

{% hint style="info" %}
**Where do these numbers come from?** Submission statistics on the dashboard are computed from Elasticsearch indexes, not directly from each repository's MySQL database. They refresh near-instantly when a new submission arrives, but very large historical changes (e.g. deleting hundreds of submissions in one operation) can take a moment to be reflected.
{% endhint %}

## Switching active projects

You can change the active project at any time. From the **Projects** section on the dashboard, click **Set as active** next to the project you want to focus on. The dashboard reloads to show that project's forms, team, and statistics.

You can also access the full list of your projects (with the **Set as active** buttons) from the left-hand menu by clicking **Projects** — this is covered in detail in the "[Projects](projects.md)" section.

{% hint style="info" %}
**Active project vs. current project**: The dashboard always shows the **active** project. When you click into a project from the project list, the project that opens on the screen is the **current** project, which may or may not be the active one. Most pages in FormShare show this distinction in the breadcrumb. Keep it in mind when you click links like "Assistants in the active project" vs. "Assistants on this project".
{% endhint %}

## Empty dashboard

The first time you sign in, the dashboard has no active project to show. FormShare prompts you to create your first project — see "[Creating your first project](../guides/creating-your-first-project.md)".

After you create a project, FormShare marks it active automatically. The dashboard then takes its normal shape.
