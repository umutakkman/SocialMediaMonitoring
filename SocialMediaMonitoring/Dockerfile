FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy csproj and restore dependencies
COPY ["SocialMediaMonitoring.csproj", "./"]
RUN dotnet restore "SocialMediaMonitoring.csproj"

# Copy everything else and build
COPY . .
RUN dotnet build "SocialMediaMonitoring.csproj" -c Release -o /app/build

# Publish the application
FROM build AS publish
RUN dotnet publish "SocialMediaMonitoring.csproj" -c Release -o /app/publish

# Build runtime image
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Make sure your app listens on the right port
ENV ASPNETCORE_URLS=http://+:5000

EXPOSE 5000

ENTRYPOINT ["dotnet", "SocialMediaMonitoring.dll"]
