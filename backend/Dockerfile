FROM openjdk:8-jdk-alpine

ARG JAR_FILE=target/my-car-time-1.0-SNAPSHOT-jar-with-dependencies.jar

WORKDIR /app

COPY ${JAR_FILE} app.jar

EXPOSE 1337

ENTRYPOINT ["java", "-jar","app.jar"]