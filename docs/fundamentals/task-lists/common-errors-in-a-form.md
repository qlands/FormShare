# Common errors in a form

FormShare manages your data in a better way but by doing so it performs more checks on your ODK Form. Though FormShare follows ODK's official standards it has more restrictions, for example, if you have an ODK form with a variable called "repeat" it will not upload in FormShare nor in Kobo because "repeat" is an ODK restricted word, however, if you have a variable called "abstract" the ODK form will upload in Kobo but not in FormShare because "abstract" is a restricted word in FormShare. **For this reason, if you have an ODK Form that works on other platforms it might need some modifications to work with FormShare**. The platform will inform you about the error and how to correct it.

This section provides information about the common errors in a form

## The primary key does not exist

> Message from FromShare: "The primary key variable does not exist or is inside a repeat."

When you upload a form FormShare asks you to indicate a variable to use to control duplicate submissions:

<figure><img src="../../.gitbook/assets/primary_key.png" alt=""><figcaption></figcaption></figure>

The variable to control duplicate submissions must exist in your form and it must be OUTSIDE a repeat.

{% hint style="info" %}
**What is duplicate data?**

_Let’s imagine that you are surveying cattle in a rural village and each animal has an ear tag. Two enumerators, James and Patricia go around the village gathering the information for each animal. James and Patricia without realizing it, survey the same animal (the same ear tag) and send the data. To solve this problem and prevent having the same animal twice in our dataset, you can tell FormShare that the ear-tag variable **must be unique**. In this example, the **ear tag is the variable that you will use to control duplicated data**. FormShare will alert you that there is duplicated data, and you will be able to correct it easily._
{% endhint %}

## Duplicated variables

> Message from FromShare: The following variables are duplicated within repeats or outside repeats

The ODK standard allows having two or more variables with the same name as long as they are in different groups. FormShare does not allow that and will tell you which variables are repeated. Just rename the variables to fix the problem.

## Variables with invalid names

> Message from FromShare: The following variables have invalid names

This error occurs when you have a variable that is also a restricted word in FormShare. The following is a list of restricted words that you CANNOT USE as variables or repeat names.

{% embed url="https://docs.google.com/spreadsheets/d/1PsDsbFZZXnlHRdmntWzX_DDSPCm7K-6knV3qICCxAk0/edit?usp=sharing" %}

FormShare will tell you which variables have invalid names. Fix the problem by renaming the variables.

## Identical choices

> Message from FromShare: The following choices are identical.

This error happens when two or more lists in the "Choices" sheet have the same options/items. The example below has the problem, the list sex\__owner is identical to the list sex\__pet.

{% embed url="https://docs.google.com/spreadsheets/d/1VGeabvyWKHKoJG-N0-QfaonjKY3YQU2bQ6mYVF66fDk/edit?usp=sharing" %}

To fix this error you need to use only one list. The error above can be solved by having only one list called "sex" and use it for both variables. See example:

{% embed url="https://docs.google.com/spreadsheets/d/1TnY49u8EARi46fDUoys7WywhJN4zJwWgJhf3axaf4cE/edit?usp=sharing" %}
