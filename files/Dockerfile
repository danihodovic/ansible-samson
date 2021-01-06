FROM zendesk/samson:v3260

RUN apt update && apt-get install python3-pip -y
RUN pip3 install ansible==2.10.5 jmespath docker boto3 botocore

# Add github to known hosts otherwise the Samson UI freezes waiting for
# confirmation.
RUN ssh-keyscan -H github.com > /etc/ssh/ssh_known_hosts

RUN echo '\
production: 					\n\
  adapter: sqlite3 				\n\
  database: db/production.sqlite3 		\n\
  pool: <%= ENV["RAILS_MAX_THREADS"] %> 	\n\
  timeout: 5000 ' > /app/config/database.yml

# https://stackoverflow.com/questions/17150064/how-to-check-if-the-database-exists-or-not-in-rails-before-doing-a-rake-dbsetup/40019538#40019538
RUN echo '\n\
rake db:migrate 2>/dev/null || rake db:setup rake db:migrate 	\n\
bundle exec puma -C config/puma.rb' > /app/run_samson.sh && chmod +x /app/run_samson.sh

CMD ["bash", "/app/run_samson.sh"]
