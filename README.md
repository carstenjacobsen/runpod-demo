# Runpod Demo

This application can send release note notifications to slack, and create release notes for documentation. GitHub Actions can call the application when a new release is created. The 

## Architecture
The application consists of a frontend and a backend. 


## Runpod Services
The application is built using three Runpod services: [Serverless](https://docs.runpod.io/serverless/overview), [Pod](https://docs.runpod.io/pods/overview) and [Storage](https://docs.runpod.io/storage/overview).

* **Serverless**: The application uses an LLM to summarize release notes, and organize the text as bullet points. Using vLLM workers deployed as a Serverless endpoint is a convenient and easily customizable way to use LLM models.
* **Pod**: The application backend is deployed to a Pod, an affordable and scalable way to host the backend.
* **Storage**: The release notes could be stored in a database, but for the sake of simplicity, they are stored in a CSV file. Using the Storage service it's easy for the backend to write to the file, and to read the file for the frontend endpoint.


## Challenges
There are a couple of unresolved issues with the application. 

1. Cloudflare timeout (Pods)
2. Troubleshooting is hard
3. Hard to find the right model





## Learnings
Runpod is well-documented, but as a new developer using Runpod, there are unanswered questions along the way. After some trial-and-error I went back to the documentation, and then parts of it made more sense. 

The backend was initially deployed Serverless, but after long struggles to make it work, the backend was deployed to a Pod instead. 


### What would I change?
This was my first time using Runpod and deploying an application, so I had no prior experience to lean on, and experienced Runpod as any other developer deploying their first application. Some of the things that would had made my journey more smooth would be:

1. **Tutorials**: Teach developers new to Runpod core concepts and how to deploy their first endpoints, Pods, storage volumes etc. Focus should not only be on how to do it, but also learning how to make the right decisions when you build and deploy on Runpod.
2. **Guides**: Step-by-step guides that show how to use Runpod for different use cases, and how to build for scale. The guides assume the developer has at least basic knowledge about Runpod (maybe acquired from the tutorials), and now they want to use Runpod for their production application.


The good thing is, there's a lot of information in the documentation. 

_2026, Carsten Jacobsen_











