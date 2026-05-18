---
description: Partners are external data-access agents — donors, regulators, analysts — who can view and download data from selected projects or forms without being collaborators or assistants.
---

# Partners

A **partner** is an external party who has been granted read-only access to data in your projects. Partners are useful when you need to share submissions with people who are not part of your team — donors checking project progress, regulators reviewing compliance data, statisticians running analyses, or downstream platforms pulling data through the API.

Partners are different from [collaborators](members.md) (who help you manage projects and forms) and from [assistants](tasks/) (who collect or clean data). Partners only consume data; they cannot upload, edit, or delete anything.

{% hint style="info" %}
**Partner access is an optional feature.** Partner support is not enabled by default in a FormShare installation. If you don't see "Partners" in the menu or on the project details page, see the "[Partner settings](../technical-pages/settings.md#partners)" page for how to activate this feature on your instance, or ask your administrator.
{% endhint %}

## What partners can do

A partner can:

* Sign in through a dedicated **Partner Access** portal (separate from the main FormShare sign-in).
* See a list of projects and forms they have been granted access to.
* View the form details, the map of submissions, and the data dictionary.
* Download the data products (CSV, Excel, JSON, KML, etc.) that you have made available to them — limited to **public** products by default. See "[Private vs public products](../data-management/data-products/private-vs-public-products.md)".
* Pull data through the API using their API key.

A partner cannot:

* Modify any data or metadata.
* See submissions outside the projects or forms they are linked to.
* Access sensitive fields you have marked as such — those are masked from partners. See "[Marking fields as sensitive](../data-management/data-dictionary/marking-sensitive-fields.md)".

## Managing partners

> Add screenshot of the "Manage partners" page with the partner list and "Add partner" button.

From the left-hand menu, click **Partners** to open the partner-management page. From here you can add new partners, edit existing ones, change passwords, regenerate API keys, view per-partner activity logs, and remove partners that are no longer needed.

### Add a partner

Click **Add partner**. The "Add partner" form will appear. You need to provide:

* **Name**: The full name of the partner — typically the person or contact within the partner organization.
* **Organization**: The name of the partner organization (e.g. "Ministry of Health", "Acme Foundation"). This is required and appears in audit logs.
* **Email**: The email the partner will use to sign in. Two partners cannot share the same email within your FormShare instance.
* **Telephone**: A contact number for the partner. Required.
* **Time zone**: The time zone of the partner. Timestamps shown to the partner will be expressed in this zone.
* **Password and password confirmation**: The password the partner will use to sign in. The partner can change this themselves after their first sign-in.

Click **Add partner**. FormShare creates the partner record, generates an **API key** for programmatic access, and returns you to the partner list.

### Edit a partner

Click any partner in the list to open the edit page. You can update the partner's contact information, regenerate the API key, or activate / deactivate the account. A deactivated partner cannot sign in, but the historical activity log is preserved.

### Partner activity log

Each partner has an **Activity** view that lists every action they have performed — sign-ins, project access, data downloads. Use it to audit data sharing or to investigate suspicious activity.

### Delete a partner

Click **Delete** next to the partner in the list. FormShare will ask you to confirm. Deleting a partner removes their ability to sign in but preserves the activity log entries created while they were active.

## Linking a partner to data

Creating a partner does not by itself grant access to any data. After the partner exists, you link them to specific projects or forms.

### Link to a project

On the **Project Details** page, the **Project partners** section lists who has access to this project. Click the **+** to link a new partner. You can configure:

* **Time window**: The date range during which the partner can access this project. Leave the start date empty for access starting immediately; leave the end date empty for indefinite access.
* **Access scope**: The partner can be given access to *all* forms in the project, or to a filtered subset.
* **Query filter** (optional): A SQL-like filter on submissions. Useful when a partner should only see records that match certain criteria — e.g. submissions from a specific region or above a certain date.

A partner linked to a project automatically receives access to every form inside it, subject to the filter you set.

### Link to a single form

If you only want a partner to see one form, link them to the form directly from the form details page. Form-level links use the same time-window and query-filter mechanics as project-level links.

{% hint style="warning" %}
**Project links override form links.** If a partner is linked at the project level, the project-level configuration applies to every form in the project. Linking them to an individual form on top of that does not narrow their access — it broadens it. To restrict a partner to a single form, link them to that form only, not to the parent project.
{% endhint %}

## Partner sign-in

Partners do not use the main FormShare sign-in page. Each FormShare instance exposes a separate partner sign-in URL (e.g. `https://your-formshare-instance/partner_login`) that is restricted to partner accounts. Share that URL with your partners along with their credentials.

> Add screenshot of the Partner Access portal landing page.

After signing in, the partner sees their dashboard with the list of projects and forms they have access to, and can download the data they are entitled to.
