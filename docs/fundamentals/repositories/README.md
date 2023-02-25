# Repositories

For each ODK form that you upload into FormShare, the system can create a database to hold its submissions. This database is called a “repository”. At first, forms are uploaded in a “testing” stage (without a repository) but then you must create a repository for them to store “real” data. The reason for a testing stage is that it is easier to replace a form without a repository because FormShare does not need to alter the underlying database, however, it is possible to [merge new versions of a form into a common repository](merging-subversions-of-a-form.md).

<mark style="color:red;">**After you tested any form**</mark> you can generate a repository for it.

![](../../.gitbook/assets/form\_test\_stage\_03\_captions.png)

1. To create a repository for your form click either the button "Create repository" or the link "create a repository for the form". The repository creator will appear.

![](../../.gitbook/assets/create\_repository\_captions.png)

1. If you have testing data you can automatically import it into the repository (default) however, you can discard/delete all testing data.
2. To create the repository click on the "Create repository" button.

{% hint style="info" %}
Note: If your form has multiple languages the repository creator will ask for more details. This is covered in the section "[Forms with multiple languages](forms-with-multiple-languages.md)".
{% endhint %}

FormShare will start generating your repository

![](../../.gitbook/assets/generating\_repository.png)

After the process is complete, FormShare will take you to the [Form Details](../forms/#the-repository-stage) page.
