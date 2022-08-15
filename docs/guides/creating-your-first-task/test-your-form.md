# Test your form

Your form is now ready for collecting testing data.&#x20;

{% hint style="info" %}
We have noticed that 90% of the users do not test their forms before generating a repository. Even though FormShare allows [merging different versions of a form](../../fundamentals/repositories/merging-subversions-of-a-form.md) into one common repository, such a procedure is simpler when the form is in a testing stage.

**Why do I need to test my form?**

Though FormShare checks for certain errors in your form it does not check:

* Logic problems. For example, if a question is not asked due to a wrong condition.
* Is very common to miss a question and a field test can spot such problems.
* Field agents might not understand the survey and more notes are required.
{% endhint %}

![](../../.gitbook/assets/form\_test\_stage\_01\_captions.png)

1\. Configure Collect: Use the QR code to configure ODK Collect. You can also use the ODK URL to manually configure it.

2\. Important note: This form is in the testing stage. This means that you can update it at all times and **submissions are for testing purposes**. When you finished testing the form you can create a repository for the form and start collecting "real" data.

{% hint style="warning" %}
**Remember**: <mark style="color:red;">**Submissions received to a form in the testing stage are considered test data**</mark>. This means that any <mark style="color:red;">**submissions will be discarded**</mark> every time that you upload a new version of the form.

This behavior **is not the same** when your form has a repository. The section "[Merging subversions of a form](../../fundamentals/repositories/merging-subversions-of-a-form.md)" discusses how to perform updates to a form with a repository.
{% endhint %}

3\. Statistics: This section show statistics about your testing data. This information will change every time you receive new submissions. When you have submissions with GPS data you can explore each submission

4\. Basic downloads: During the "testing stage" you can download the testing data in CSV format (Flat CSV / One file) and download any media submitted with the submissions. These are basic downloads. **More download formats will be available after you create a repository.**

![](../../.gitbook/assets/submission\_details\_captions.png)

1. Explore a submission: Click on any location on the map to see the information attached to its submission.
2. Submission ID: Each submission in FormShare is stored with a unique ID. See the section "[How does FormShare stores my data?](../../fundamentals/repositories/how-does-formshare-stores-my-data.md)" for more information.
3. Submission data: Each submission will show its data. Please note that FormShare only shows here the data outside a repeat. See the section "[How does FormShare stores my data?](../../fundamentals/repositories/how-does-formshare-stores-my-data.md)" for more information. If your submission has media like images, videos, or sound a new tab will appear for you to explore such media.

Once you are satisfied with the testing. You can create a repository to start collecting "Real" data.
