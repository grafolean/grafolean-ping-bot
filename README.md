# About Grafolean Ping Collector

This package is a Ping Collector for Grafolean, an easy to use generic monitoring system.

Once installed, all the configuration of Ping sensors is done through Grafolean's web-based user interface. Depending on permissions,
a single Ping Collector instance can be fetching data for multiple accounts and entities. The fetching intervals can be specified with
up to a second precision.

Requirements:
- the devices will be pinged *from the container* (make sure Ping Collector is installed in the correct network and that there are no firewalls in between)
- Grafolean must be accessible via HTTP(S)

# License

License is Commons Clause license (on top of Apache 2.0) - source is available, you can use it for free (commercially too), modify and
share, but you can't sell it to third parties. See [LICENSE.md](https://gitlab.com/grafolean/grafolean-collector-ping/blob/master/LICENSE.md) for details.

If in doubt, please [open an issue](https://gitlab.com/grafolean/grafolean-collector-ping/issues) to get further clarification.

# Install (docker / docker-compose)

Docker is the easiest and currently the only officially supported way. Note that while instructions might (with possibly some modifications) work on other operating systems, Linux is assumed.

1) log in to Grafolean service (either https://grafolean.com/ or self-hosted), select an appropriate `Account` and create a new `Bot`. Make sure that selected protocol is `Ping`. Copy the bot token.

2) save [docker-compose.yml](https://gitlab.com/grafolean/grafolean-collector-ping/raw/master/docker-compose.yml) to a local file:
    ```
    $ mkdir ~/pingcollector
    $ cd ~/pingcollector
    $ wget https://gitlab.com/grafolean/grafolean-collector-ping/raw/master/docker-compose.yml
    ```

3) These settings must be set:

    - mandatory: `BACKEND_URL` (set to the URL of Grafolean backend, for example `https://grafolean.com/api`),
    - mandatory: `BOT_TOKEN` (set to the bot token from step 1),
    - optional: `JOBS_REFRESH_INTERVAL` (interval in seconds at which the jobs definitions will be updated)

   The easiest way to set them is to download example `.env` and edit it:
    ```
    $ wget https://gitlab.com/grafolean/grafolean-collector-ping/raw/master/.env.example -O .env
    $ nano .env
    ```

4) run: `docker-compose up -d`

If you get no error, congratulations! Everything else is done from within the Grafolean UI. You can however check the status of container as usually by running `docker ps`, and investigate logs by running `docker logs -f grafolean-collector-ping`.

In case of error make sure that the user is allowed to run `docker` (that is, that it is in `docker` group) by running `docker ps`. Alternatively, container can be run using `sudo` (line 4 then reads `sudo docker-compose up -d`).

## Upgrade

Upgrading should be easy:

1) `$ docker-compose pull`
2) `$ docker-compose down`
3) `$ docker-compose up -d`

## Debugging

Container logs can be checked by running:
```
$ docker logs --since 5m -f grafolean-collector-ping
```

## Building locally

If you wish to build the Docker image locally (for debugging or for development purposes), you can specify a custom docker-compose YAML file:
```
docker-compose -f docker-compose.dev.yml build
```

In this case `.env.example` can be copied to `.env` and all settings can be altered there, which helps us avoid commiting settings to the repository.

# Development

## Contributing

To contribute to this repository, CLA needs to be signed. Please open an issue about the problem you are facing before submitting a pull request.

## Issues

If you encounter any problems installing or running the software, please let us know in the [issues](https://gitlab.com/grafolean/grafolean-collector-ping/issues). Please make an effort when describing the issue. If we can reproduce the problem, we can also fix it much faster.
