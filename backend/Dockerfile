FROM maven:alpine as BUILD

COPY . .
RUN mvn package

FROM openjdk:8-jdk-alpine
WORKDIR /app
COPY --from=BUILD target/my-car-time-1.0-SNAPSHOT-jar-with-dependencies.jar app.jar

EXPOSE 1337

ENTRYPOINT ["java", "-jar","app.jar"]