FROM gradle:9.3.0-jdk21 AS build
WORKDIR /src
COPY . .
RUN gradle --no-daemon bootJar

FROM eclipse-temurin:21-jre
RUN useradd --system --uid 10001 gateway
WORKDIR /app
COPY --from=build /src/build/libs/*.jar app.jar
USER gateway
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
