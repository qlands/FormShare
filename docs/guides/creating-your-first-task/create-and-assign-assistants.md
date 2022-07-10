# Create and assign assistants

After uploading a new form, FormShare will take you to the form details page.

![](../../.gitbook/assets/form\_details\_01\_captions.png)

1\. Testing stage: Every form that you upload to FormShare is stored first in a **testing stage**. This means that FormShare hasn't created a [repository for it](../../fundamentals/repositories/how-formshare-stores-data.md). The testing stage allows you to test your form and easily update it with fixed versions without the need of [merging data into a repository](../../data-management/for-designers/working-with-submissions.md).

{% hint style="warning" %}
Important Note: <mark style="color:red;">**Submissions received to a form in the testing stage are considered test data**</mark>. This means that any <mark style="color:red;">**submissions will be discarded**</mark> every time that you upload a new version of the form.

This behavior **is not the same** when your form has a repository. The section "[Working with submissions](../../data-management/for-designers/working-with-submissions.md)" discusses how to perform updates to a form with a repository.
{% endhint %}

2\. Active: A form can be "active" or "inactive". An active form can receive submissions. You can change the status of a form by editing it.

3\. Geo-referenced. This tag will appear when a form has a geolocation variable.

4\. Delete: The delete button deletes the forms and all their data.

{% hint style="info" %}
FormShare does not physically (from the hard drive) removes any data. If you remove a form FormShare will remove it from the FormShare database and will not be accessible through the interface but its repository in MySQL will remain intact but marked as deleted. The same for any files and products generated in the form. The section "[How FormShare stores data](../../fundamentals/repositories/how-formshare-stores-data.md)" covers more details about this.
{% endhint %}

5\. Update ODK Form: As indicated in point 1 above, forms in a testing stage can be updated easily at any time. But remember: <mark style="color:red;">**Submissions received to a form in the testing stage are considered test data**</mark>. This means that any <mark style="color:red;">**submissions will be discarded**</mark> every time that you upload a new version of the form.

6\. Downloads: Submissions received to a form in the testing stage are considered test data. At this stage, FormShare provides minimal download types:

* Download ODK form: This will download the ODK form in Excel format
* Download data in CSV format: This is a "Flat CSV file". FormShare does not resolve any label names for data in the testing stage.&#x20;
