# Create a repository for your form

{% hint style="info" %}
**FormShare stores submission data in a repository**. Details of this are covered in the section "[How does FormShare stores my data?](../../fundamentals/repositories/how-does-formshare-stores-my-data.md)".
{% endhint %}

For each ODK form that you upload into FormShare, the system creates a database to hold its submissions. This database is called a “repository”. At first, forms are uploaded in a “testing” stage (without a repository) but then you can create a repository for them to store “real” data. The reason for a testing stage is that it is easier to replace a form without a repository because FormShare does not need to alter the underlying database, however it is possible to [merge new versions of a form into a common repository](../../fundamentals/repositories/merging-subversions-of-a-form.md).

<mark style="color:red;">**After you tested your form**</mark> you can generate a repository for it.

![](../../.gitbook/assets/form\_test\_stage\_03\_captions.png)

1. To create a repository for your form click either the button "Create repository" or the link "create a repository for the form". The repository creator will appear.

![](../../.gitbook/assets/create\_repository\_captions.png)

1. If you have testing data you can automatically import it into the repository (default) however, you can discard/delete all testing data.
2. To create the repository click on the "Create repository" button.

{% hint style="info" %}
Note: If your form has multiple languages the repository creator will ask for more details. This is covered in the section "[Forms with multiple languages](../../fundamentals/repositories/forms-with-multiple-languages.md)".
{% endhint %}

FormShare will start generating your repository

![](../../.gitbook/assets/generating\_repository.png)

Afterward, the "Form details" page will appear with more options and utilities.

![](../../.gitbook/assets/form\_details\_with\_repo\_captions.png)

1. **With repository**: The form now appears with a repository.
2. **In database**: Submissions are now stored in a database. You can start cleaning the data using the [Web Interface ](../../data-management/for-designers/figma-integration/the-web-interface.md)or through [API](../../data-management/for-designers/figma-integration/api-data-cleaning.md).
3. **With error**:  Submissions that don't enter the database go to the [error log](../../data-management/for-designers/submissions-with-errors.md).
4. **Log entries**: The process of cleaning submissions with errors generate traceability records in the [error log](../../data-management/for-designers/submissions-with-errors.md). You can review them at any time.
5. **Merge new version**: It is normal to have new versions of a form even after substantial testing. A new version of a form will store the submissions in the same repository of its previous version. **This means that you WILL NOT have two different sets of data that then you would need to join**. This is covered in more detail in the section "[Merging subversions of a form](../../fundamentals/repositories/merging-subversions-of-a-form.md)".
6. **Anonymize fields**: You can mark fields as sensitive across all tables. Fields marked as sensitive will not appear in [public products](../../data-management/data-products/private-vs-public-products.md).
7. **Manage submissions**: This feature allows you to delete submissions or move a submission from the database into the log entries. This is covered in more detail in the section "[Working with submissions](../../data-management/for-designers/working-with-submissions.md)".
8. **Import external data**: FormShare allows you to import data from FormShare 1.0 (JSON), ODK Central (XML), and third-party platforms in JSON format. This is covered in more detail in the section "[Import external data](../../fundamentals/submissions/import-external-data.md)"
9. **The audit log**: FormShare logs any change in the data regardless of the method used (e.g., Web interface, API, etc). This is covered in more detail in the section "[The audit log](../../data-management/for-designers/figma-integration/the-audit-log.md)".
10. **Export data**: Now that the form has a repository, it is possible to export the data in different formats like Excel, and JSON. This is covered in more detail in the section "[Data products](../../data-management/data-products/)".
