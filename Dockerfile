FROM python:3.11-slim

WORKDIR /app

COPY #add depenedencies 

RUN npm install

COPY . .

ENV PORT=3000

EXPOSE 9000

CMD ["npm", "start"]