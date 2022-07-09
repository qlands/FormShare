# Uploading your first ODK Form

After creating a new project, FormShare will take you to the projects details page. In an empty project, you are directed to upload a new form.

![](../.gitbook/assets/empty\_project\_captions.png)

1. Active project: Click on this link to access the details of the active project.
2. Collaborators: Click on this link to access the list of collaborators in the <mark style="color:red;">**active**</mark> project.
3. Assistants: Click on this link to access the list of assistants in the <mark style="color:red;">**active**</mark> project.
4. Assistant groups: Click on this link to access the list of assistant groups in the <mark style="color:red;">**active**</mark> project.
5. Edit project: Click on the "Edit Project" button to edit the details of the project.
6. Delete project: Click on the "Delete Project" button to delete the project and its forms.
7. Project files: Projects can hold files. For example the data management plans and policies in PDF format. Project files are available to collaborators.
8. Assistant groups: This tab shows the list of collaborators in the <mark style="color:red;">**current**</mark> project.
9. Assistants: This tab shows the list of assistant groups in the <mark style="color:red;">**current**</mark> project.
10. Map: This tab shows the geographical position of each submission in each form of the project.  Each point will be shown with a different color depending on the color of the form.
11. Collaborators: This tab shows the list of collaborators in the <mark style="color:red;">**current**</mark> project.
12. Add a new form: Click on the "Add New Form" button to upload a new form.

{% hint style="info" %}
Active vs current projects: Active project is the project shown in the dashboard and that is accessible on the left side menu of FormShare. The current project refers to the current project on the screen.
{% endhint %}

The "Add New Form" button will show the "Upload new form" screen.

![](../.gitbook/assets/upload\_form.png)

To upload a new form, you need to provide the following information:

* Survey file (XLS / XLSX): This is the ODK form file in Excel format.
* Variable used to control duplicate submissions: To control duplicate submissions, you need to select a variable from your ODK Form whose values will be **UNIQUE** across all the submissions that you expect to have. If you need to join two or more variables to become UNIQUE, then use an ODK Calculate to merge them into one variable. This variable will become the Primary Key of your ODK Form and CAN NOT BE CHANGED afterward.

{% hint style="info" %}
**What is duplicate data?**

_Let’s imagine that you are surveying cattle in a rural village and each animal has an ear tag. Two enumerators, James and Patricia go around the village gathering the information for each animal. James and Patricia without realizing it, survey the same animal (the same ear tag) and send the data. To solve this problem and prevent having the same animal twice in our dataset, you can tell FormShare that the ear-tag variable **must be unique**. In this example, the **ear tag is the variable that you will use to control duplicated data**. FormShare will alert you that there is duplicated data, and you will be able to correct it easily._
{% endhint %}

* Expected number of submissions (optional): If you have a target value of submissions FormShare will show your progress towards that target.

If there are problems with your form, FormShare will tell you the problem and enable you to correct it.&#x20;

![](../.gitbook/assets/form\_error.png)

{% hint style="info" %}
**Why my form uploads fine on other platforms but not on FormShare?**

FormShare creates a [MySQL database for each form](../fundamentals/repositories/how-formshare-stores-data.md). This has several advantages compared to other platforms but it poses more restrictions. For example, the image above indicates that you cannot have a variable called "name". This is because "name" is a restricted keyword in MySQL or SQL language.

The section "[Common errors in a Form](../fundamentals/task-lists/common-errors-in-a-form.md)" provides information about each error that FormShare would detect in your form.
{% endhint %}

If the form is fine, FormShare will take you to the details of your form. Afterward, you will be able to create and assign assistants and start collecting your data.
