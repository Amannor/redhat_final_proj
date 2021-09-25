# Test prioritization in the CI\CD cycle (Red Hat OpenShift case study)
This is the code for the final project in the course "Workshop: Projects with the Industry and Academia" (IDC, Herzliya August 2021)

#### Project Status: [Completed]

## Project Intro/Objective

The purpose of this project is to be a POC in test prioritization as part of a CI\CD cycle.
More specifically, in this project we aimed at showing the feasibility of a specific test prioritization scheme in a Red Hat project.
The test prioritization scheme is based on the article ["Selective Test Prediction" by Facebook reseacrh](https://research.fb.com/wp-content/uploads/2020/12/Predictive-Test-Selection.pdf) (hereinafter referd to as "the FB article").
The Red Hat product we implemented this on is the [OpenShift project](https://github.com/openshift/origin).
As will be detailed below, the heavy lifting of this implementation (both in coding and computation resources) was creating a coherent and relevant dataset.


### Partner
* [Red Hat Inc.]
* https://www.redhat.com/en
* Partner contact: [Name of Contact], [slack handle of contact if any] - TODO - write Ilya's mail? (maybe also Gil's...?)
### Methods Used
* Robi TODO - write the ML methods you used 
* bla bla
* bla bla bla 
* etc.

### Technologies
* Robi TODO - write the main libraries you used 
* Python (version 3.9.0)
* PyCharm 

## Project Description
The main challenge in this project was getting the raw data, identifying and extracting the relevant parts and finally prepare in a scheme like in the FB article.
The first challenege was to choose a project that has enough "meat" (e.g. pull requests, large data suites etc.). With the advice of Gil Klein

(Provide more detailed overview of the project.  Talk a bit about your data sources and what questions and hypothesis you are exploring. What specific data analysis/visualization and modelling work are you using to solve the problem? What blockers and challenges are you facing?  Feel free to number or bullet point things here)

## Project History and Evolution

The main challenge in this project was getting the raw data, identifying and extracting the relevant parts and finally prepare in a scheme like in the FB article.
The first challenege was to choose a project that has enough "meat" (e.g. pull requests, large data suites etc.). With the advice of Gil Klein from Red Hat, the OpenShift project was selected. 
The second part was a long and tedious cycle of trial & error that invloved vieweing and analyzing the structure of OpenShift's CI system, its test-running outputs, the way it ran tests and documented their state (e.g. fai\success\skip etc.). Eventually we were able to find a good-enough way to track the test's "name"\"identifier" (also referd to as test's "locator" in RedHat's parlance) and a mapping from it to the file that contains that test in the [OpenShift project's repo](https://github.com/openshift/origin).

## Getting Started

1. Clone this repo (for help see this [tutorial](https://help.github.com/articles/cloning-a-repository/)).
2. Raw Data is being kept [here](Repo folder containing raw data) within this repo.

    *If using offline data mention that and how they may obtain the data from the froup)*
    
3. Data processing/transformation scripts are being kept [here](Repo folder containing data processing scripts/notebooks)
4. etc...

*If your project is well underway and setup is fairly complicated (ie. requires installation of many packages) create another "setup.md" file and link to it here*  

5. Follow setup [instructions](Link to file)

## Featured Notebooks/Analysis/Deliverables
* [Notebook/Markdown/Slide Deck Title](link)
* [Notebook/Markdown/Slide DeckTitle](link)
* [Blog Post](link)


## Contributing Members

**Team Members (Contacts) : [Alon Mannor](https://github.com/amannor)] [Rubi Arviv](https://github.com/rubiarviv)**

#### Other Members:
TODO - write Ilya and\or Gil?
|Name     |  Slack Handle   | 
|---------|-----------------|
|[Full Name](https://github.com/[github handle])| @johnDoe        |
|[Full Name](https://github.com/[github handle]) |     @janeDoe    |

## Contact
* If you haven't joined the SF Brigade Slack, [you can do that here](http://c4sf.me/slack).  
* Our slack channel is `#datasci-projectname`
* Feel free to contact team leads with any questions or if you are interested in contributing!

#### Misc
This README template was taken from: https://github.com/sfbrigade/data-science-wg/blob/master/dswg_project_resources/Project-README-template.md
