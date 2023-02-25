# Merging subversions of a form

For each ODK form that you upload into FormShare, the system can create a repository to hold its submissions. The repository matches the structure of a form. See for example the image below.

<figure><img src="../../.gitbook/assets/merge_info_01 (3).png" alt=""><figcaption></figcaption></figure>

The table that stores submissions match the structure of the survey. In this version of the survey we have the variable "producer\_age" as categorical, "province" as text and we have a typo in the label for the option "f" in list\_name "sex".

A new version of the survey fixes the typo but also changes "producer\_age" to a continuous variable and "province" to a select\_one. See below.

<figure><img src="../../.gitbook/assets/merge_info_02 (1).png" alt=""><figcaption></figcaption></figure>

Since FormShare creates a repository that matches the structure of a form any new version of a form must store the submissions in the repository of its first version. This process is called "Merging" and basically FormShare merges the **incremental changes** made on a form by adapting the repository to store such changes.

{% hint style="info" %}
Incremental changes mean changes that modify variables or that add new variables to the repository. For example, if in a new version of the above form the variable "producer\_name" is removed then the process of merging **WILL NOT** remove the column "producer\_name" from the repository.
{% endhint %}

