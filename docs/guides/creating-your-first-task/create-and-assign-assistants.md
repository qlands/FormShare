# Create and assign assistants

After uploading a new form, FormShare will take you to the form details page.

![](../../.gitbook/assets/form\_details\_01\_captions.png)

1\. Testing stage: Every form that you upload to FormShare is stored first in a **testing stage**. This means that FormShare hasn't created a [repository for it](../../fundamentals/repositories/how-does-formshare-stores-my-data.md). The testing stage allows you to test your form and easily update it with fixed versions without the need of [merging data into a repository](../../data-management/for-designers/working-with-submissions.md).

{% hint style="warning" %}
Important Note: <mark style="color:red;">**Submissions received to a form in the testing stage are considered test data**</mark>. This means that any <mark style="color:red;">**submissions will be discarded**</mark> every time that you upload a new version of the form.

This behavior **is not the same** when your form has a repository. The section "[Working with submissions](../../data-management/for-designers/working-with-submissions.md)" discusses how to perform updates to a form with a repository.
{% endhint %}

2\. Active: A form can be "active" or "inactive". An active form can receive submissions. You can change the status of a form by editing it.

3\. Geo-referenced. This tag will appear when a form has a geolocation variable.

4\. Delete: The delete button deletes the forms and all their data.

{% hint style="info" %}
FormShare does not physically (from the hard drive) removes any submissions. If you remove a form FormShare will remove it from the FormShare database and will not be accessible through the interface but its repository in MySQL will remain intact but marked as deleted. The same for any files and products generated in the form. The section "[How FormShare stores data](../../fundamentals/repositories/how-does-formshare-stores-my-data.md)" covers more details about this.
{% endhint %}

5\. Update ODK Form: As indicated in point 1 above, forms in a testing stage can be updated easily at any time. To update the form click on the "Update ODK Form" button. The "Upload new version" window will appear:

![](../../.gitbook/assets/upload\_new\_version.png)

To upload a new version of a form, you need to provide the following information:

* Survey file (XLS / XLSX): This is the updated ODK form file in Excel format.
* Variable used to control duplicate submissions: FormShare will indicate the current variable used to control duplicate submissions.

{% hint style="info" %}
Remember: To control duplicate submissions, you need to select a variable from your ODK Form whose values will be **UNIQUE** across all the submissions that you expect to have. If you need to join two or more variables to become UNIQUE, then use an ODK Calculate to merge them into one variable. This variable will become the Primary Key of your ODK Form and CAN NOT BE CHANGED afterward.
{% endhint %}

{% hint style="warning" %}
**Remember**: <mark style="color:red;">**Submissions received to a form in the testing stage are considered test data**</mark>. This means that any <mark style="color:red;">**submissions will be discarded**</mark> every time that you upload a new version of the form.
{% endhint %}

6\. Downloads: Submissions received to a form in the testing stage are considered test data. At this stage, FormShare provides minimal download types:

* Download ODK form: This will download the ODK form in Excel format
* Download data in CSV format: This is a "[Flat CSV file](../../data-management/data-products/flat-csv-one-csv-file.md)". FormShare does not [resolve option labels or multi-select fields](../../fundamentals/repositories/how-does-formshare-stores-my-data.md) for data in the testing stage.
* Download submitted media: This is a Zip file containing any media submitted to the form. Media files will be separated by [submission ID](../../fundamentals/submissions/).

7\. Form files: ODK forms can use supporting files when collecting data. These files can be data or media files. If your form uses data files, e.g., CSV files, FormShare will alert you if such files are missing. FormShare will finish checking your form once you attach all necessary data files.

![](../../.gitbook/assets/add\_files\_and\_check\_pending.png)

To add a file click on the "+" button. You can select one or more files and decide to overwrite or not current files.

{% hint style="warning" %}
Case sensitive file names: FormShare is case sensitive, therefore if you declare a file in your ODK form called "Regions.csv" then you need to attach "**R**egions.csv" and not "**r**egions.csv".
{% endhint %}

8\. Add new assistants: At this stage, you don't have any project-level assistants. Click on the "Add an assistant" button to add a new assistant. The "Add Assistant" screen will appear.

![](../../.gitbook/assets/add\_assistant.png)

To add a new assistant you will need to provide the following information:

* Assistant ID: This is a simple name to identify the assistant in FormShare. It is the name that the assistant will use in ODK Collect.

{% hint style="info" %}
The assistant id must be unique **across your account** and cannot be changed afterward.&#x20;
{% endhint %}

{% hint style="info" %}
An assistant is defined in a project **but can be used** across several projects
{% endhint %}

* Full name: The full name of the assistant.
* Email: The email of the assistant.
* Time zone: This should be the time zone where the assistant performs activities.
* Telephone: This is the telephone of the assistant. Optional.
* Password: This is the password that the assistant will use in ODK Collect.
* Share among projects: Since an assistant id must be unique across your account you can have one assistant in a project assisting other projects. Turn this check on (green) to allow this assistant to assist in other projects.

9\. Assigned assistants: Assistants help you to collect and clean data. Once you have one or more assistants in your project you can assign them to a form. Click on the "+" button to assign an assistant to the form. The "Adding assistant" screen will appear.

![](../../.gitbook/assets/assign\_assisstant.png)

An assistant can submit data and/or clean data. Click on the "Add assistant" button to add the assistant to the form.

10\. Assigned assistant groups. You can assign groups to a form in the same way that you assign assistants. Each group can submit data and/or clean data. Details on assistant groups are covered in the section "[Assistants](../../fundamentals/tasks/)".

At this stage, your form will be ready for testing. The next section covers more details on the testing stage.
