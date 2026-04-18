Use phpMyAdmin to set up the NewsHub database:

1. Open phpMyAdmin.
2. Import [newshub.sql](/C:/Users/hp/Desktop/projet%20angular/NewsHub/api/database/newshub.sql).
3. Copy [api/.env.example](/C:/Users/hp/Desktop/projet%20angular/NewsHub/api/.env.example) to `api/.env` or set the same environment variables in your terminal.
4. Start the FastAPI backend after MySQL is running.

Default local settings assume:
- host: `127.0.0.1`
- port: `3306`
- user: `root`
- password: empty
- database: `newshub`
