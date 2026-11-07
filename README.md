# SIPORA

SIPORA (Sistem Pelaporan dan Aspirasi) is a school reporting web application for SMP Budi Mulia Desa Putera. It turns stakeholder needs into confidential case management for bullying reports, facility issues, counseling requests, aspirations, and teacher evaluations.

Role-based access rules protect reporter identities and let counselors and school administrators handle submitted cases.

## Application features

- Case forms and status tracking for bullying and facility reports.
- Counseling requests, student aspirations, and teacher evaluations.
- Access rules for reporters, teachers, counselors, and school administrators.
- REST APIs (web endpoints) for case submission, review, status updates, and responses.
- An audit trail that records case creation, edits, status changes, and soft deletes. Each entry stores its time, user identifier, and previous values.

A soft delete hides a record while keeping its history. The audit trail supports case review throughout the reporting process.

## Application structure

SIPORA has two web applications. The frontend provides pages for students and staff. The backend provides the API and stores application data in PostgreSQL.

| Component | Repository | Technology | Deployment |
| --- | --- | --- | --- |
| Frontend | [sipora-fe](https://github.com/bizarrebeam/sipora-fe) | Vue 3, TypeScript, Vite, and Pinia | [Open SIPORA](https://sipora-fe.vercel.app) |
| Backend | [sipora-be](https://github.com/bizarrebeam/sipora-be) | Python, Django REST Framework, and PostgreSQL | Railway deployment history |

The frontend calls the backend API. Each repository can deploy on its own. The frontend is available at [sipora-fe.vercel.app](https://sipora-fe.vercel.app). The saved Railway backend URL is [web-production-150eb.up.railway.app](https://web-production-150eb.up.railway.app). It returned 404 for the tested API paths on 7 November 2026. GitHub keeps deployment records for the [frontend](https://github.com/bizarrebeam/sipora-fe/deployments) and [backend](https://github.com/bizarrebeam/sipora-be/deployments).

The backend validates requests, applies access rules, manages case status, and records activity. It uses Django REST Framework and PostgreSQL.

## Local setup

You need Python 3.12 and a local PostgreSQL database.

1. Copy `.env.example` to `.env`.
2. Set local values in `.env`. Do not use production credentials.
3. Create a Python virtual environment and install `requirements.txt`.
4. Run `python manage.py migrate`.
5. Run `python manage.py runserver`.

The saved Railway backend URL is [web-production-150eb.up.railway.app](https://web-production-150eb.up.railway.app). It returned 404 for the tested API paths on 7 November 2026. Its deployment records are on the [GitHub deployments page](https://github.com/bizarrebeam/sipora-be/deployments).


## Course and contributors

Developed to fulfill the Proyek Pengembangan Sistem Informasi course at Universitas Indonesia in 2026.

| Name | NPM | Affiliation |
| --- | --- | --- |
| Adelya Amanda | 2306165616 | Information Systems, Universitas Indonesia |
| Joanne Kenisa Adelina Limena | 2306275626 | Information Systems, Universitas Indonesia |
| Rizki Hidayatul Laeli | 2306245491 | Information Systems, Universitas Indonesia |
| Kadek Savitri | 2306203236 | Information Systems, Universitas Indonesia |
| Theresia Tarianingsih | 2306208810 | Information Systems, Universitas Indonesia |
## Project documents

- [Product requirements document](docs/PRD_SIPORA.pdf)
- [Pitch deck](docs/Pitch%20Deck_SIPORA.pdf)
