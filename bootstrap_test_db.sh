#!/usr/bin/env bash
RAILS_DUMP_SCHEMA=false bundle exec rake db:create db:schema:load db:migrate

statements="
insert into users (name, role_id) values ('test_user', 3);

insert into oauth_applications
(name, uid, secret, redirect_uri, created_at, updated_at) values
('name', 'uid', 'secret', 'http://test.com', date('now'), date('now'));

insert into oauth_access_tokens
(resource_owner_id, application_id, token, scopes, created_at) values
(1, 1, 'token', 'default', date('now'));
"

sqlite3 /app/db/development.sqlite3 "$statements"
