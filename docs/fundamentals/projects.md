# Projects

FormShare organizes forms in projects.

## The project list

The project list shows your projects. These can be projects created by you or shared with you by your collaborators.

![](../.gitbook/assets/project\_list\_captions.png)

1. **Projects**: Click on the "Projects" link to access your list of projects
2. **Active project**: You can have one active project marked with a ⭐.
3. **Project list**: The project list shows projects created by you or shared with you by your collaborators.
4. **Create a new project**: Click on the "Create new project" button to create a [new project](projects.md#add-a-project).
5. **Set as active**: Click on the "Set as active" button to set that project as the active project.
6. **Edit**: Click on the "Edit" button to edit the description and parameters of the project.
7. **Delete**: Click on the "Delete" button to delete the project. <mark style="color:red;">**This will delete all forms and submissions in the projec**</mark>t.
8. **Statistics**: Each project shows general statistics about its forms and submissions.
9. Details: Click on each project to access its [details](projects.md#project-details).

## Add a project

![](../.gitbook/assets/add\_project\_odk.png)

To add a project you will need to provide the following information:

* Code: This is a short name to identify your project within FormShare. The name cannot have any special characters besides underscore (\_). This name must be unique across your account and **cannot be changed afterward**.
* Name: This is the full name of your project. It can contain spaces but must not exceed 120 characters.
* Color: In ODK Collect each project can have a color for easy identification.
* Icon: In ODK Collect each project can have **one** icon/emoji for easy identification.
* Time zone: This should be the time zone where submissions happen.&#x20;
* Abstract: Type here any other information regarding your project
* Use a case/longitudinal workflow (optional): Check this option if the forms within this project and their submissions will be related to cases. You can read more about this in the section "[Longitudinal data collection](../use-cases/for-engineers/)"
* Requires authentication to accept data (optional): By default, data collectors require to enter their credentials to submit data. Uncheck this option to have public/crowdsourcing submissions.

Click on the "Add project button" to add the project. If there are problems with any of the fields, FormShare will tell you the problem and enable you to correct it. When the fields are filled in correctly, FormShare will create your project and take you to the "[Project Details](projects.md#project-details)" page to upload your first form.

## Project details

The project details page shows different elements that a project has. Here you can add forms, collaborators, assistants, groups of assistants, and project files.

![](../.gitbook/assets/project\_details\_captions.png)

1. **QR for Collect**: Use this QR code to configure ODK Collect.
2. **Map**: The map shows the location of all submissions across all the forms in the project. Each submission will be colored according to the color of its form.
3. **Project details**: This section shows basic metadata attached to the project.
4. **Statistics**: This section shows some basic statistics of the project.
5. **Collaborators**: This section shows who is collaborating on the project. Click the <mark style="color:blue;">**+**</mark> button to add a collaborator.
6. **Add a new form**: Click on the "Add new form" button to add a new form to the project.
7. **Form List**: This section shows the forms contained in the project. Each form will show independent details and statistics. Click on the name of a form to access the "Form details" page.
8. **Assistants**: Assistants help you collect and clean data. Assistants are defined in a project, can collaborate across projects, and can be assigned to different forms with different privileges across projects. The section "[Assistants](tasks/)" provides more details. Click on the <mark style="color:blue;">**+**</mark> button to add a new assistant to the project.
9. **Assistant groups**: You can create groups to allocate different assistants according to different criteria. For example, you can create a group called "Data collectors" and another group called "Data cleaning team". You can attach groups to a form and assign them different privileges.
10. **Project files:** You can attach any kind of file to a project. For example, you can attach guidelines, policies, good practices, etc. These files are available to you and those collaborating with you on the project.
11. **Edit**: Click on the "Edit" button to [edit ](projects.md#undefined)the details of the project. For example, to change its description or its abstract.
12. **Delete**: Click on the "Delete" button to [delete](projects.md#undefined) the project. <mark style="color:red;">**Note: When you delete a project you will delete all its forms and submissions**</mark>**.** Deleting a project will create a log in the platform for auditing purposes.
13. **Project partners**: You can link any number of [partners](partners.md) to a project. When you link a partner to a project they can access any data of any form inside the project. You can also link partners to individual forms to allow more limited access.

{% hint style="info" %}
Note on Partners: Partners access is a feature that is not present by default in a FormShare installation. See the "[Partner settings](../technical-pages/keyboard-shortcuts.md#partners)" for information about how to activate this feature.
{% endhint %}

## Edit a project

![](<../.gitbook/assets/edit\_project\_captions (1).png>)

1. **Project code**: You cannot edit the project code.
2. **Longitudinal workflow**: This option is read-only if you already have ODK forms in your project.

## Delete a project

Before you delete a project you need to be sure that you want to proceed with such action.

![](../.gitbook/assets/delete\_project.png)

<mark style="color:red;">**Note: When you delete a project you will delete all its forms and submissions**</mark>**.** Deleting a project will create a log in the platform for auditing purposes. This log entry will contain the user deleting the project along with the date and time when the project was deleted.
