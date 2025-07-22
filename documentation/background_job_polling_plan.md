# Background Job Polling Implementation Plan

This document outlines the steps and file locations for implementing a background job system with polling for job status/results in the video processing API. The goal is to allow clients to start a long-running job (like video processing), receive a job ID immediately, and poll for the job's status and result.

---

## 1. API Endpoint to Start a Job
- **File:** `app/api/endpoints.py`
- **What to do:**
  - Update the `/process` endpoint to always return a unique job ID when a background job is started.
  - When a request is made with `background: true`, the endpoint should:
    - Generate a job ID.
    - Start the processing task in the background, passing the job ID.
    - Store the job's initial status (e.g., 'pending') in a job state store.
    - Return the job ID to the client immediately.

## 2. Background Processing Logic
- **File:** `app/core/processor.py`
- **What to do:**
  - Update the processing function (e.g., `process_video`) to accept a job ID.
  - As the job progresses, update the job's status and result in the job state store (e.g., 'in progress', 'done', 'failed', plus any result data or error messages).

## 3. Job State Storage
- **File:** `app/database/operations.py` (or create a new file, e.g., `app/database/job_status.py`)
- **What to do:**
  - Implement functions to:
    - Create a new job record with status and result fields.
    - Update job status and result as the job progresses.
    - Retrieve job status and result by job ID.
  - The storage can be in-memory (for prototyping), or use a database/Redis for persistence and scalability.

## 4. Job Status Polling Endpoint
- **File:** `app/api/endpoints.py`
- **What to do:**
  - Add a new endpoint, e.g., `/job-status/{job_id}`.
  - This endpoint should:
    - Accept a job ID as a path parameter.
    - Look up the job's status and result in the job state store.
    - Return the current status and, if available, the result or error message.

## 5. Error Handling and Cleanup
- **Files:** `app/core/processor.py`, `app/database/operations.py`
- **What to do:**
  - Ensure that any errors during processing are caught and the job status is updated to 'failed' with an error message.
  - Optionally, implement cleanup of old job records after a certain period.

---

## Summary Table

| Task                        | File(s)                        | Description                                                      |
|-----------------------------|-------------------------------|------------------------------------------------------------------|
| Start job endpoint          | `app/api/endpoints.py`         | Accepts request, starts background job, returns job ID            |
| Background job logic        | `app/core/processor.py`        | Runs processing, updates job status/result                        |
| Job state storage           | `app/database/operations.py`   | Stores and retrieves job status/result                            |
| Job status polling endpoint | `app/api/endpoints.py`         | Lets client poll for job status/result by job ID                  |
| Error handling/cleanup      | `processor.py`, `operations.py`| Updates job status on error, cleans up old jobs                   |

---

**This plan provides a clear, file-by-file roadmap for implementing robust background job polling in your API.**
