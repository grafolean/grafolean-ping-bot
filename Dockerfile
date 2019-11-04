FROM python:3.6-slim-stretch as python-requirements
COPY ./Pipfile ./Pipfile.lock /pingcollector/
WORKDIR /pingcollector
RUN \
    pip install pipenv && \
    pipenv lock -r > /requirements.txt

FROM python:3.6-slim-stretch as build-backend
COPY ./ /pingcollector/
WORKDIR /pingcollector
RUN \
    find ./ ! -name '*.py' -type f -exec rm '{}' ';' && \
    rm -rf tests/ .vscode/ .pytest_cache/ __pycache__/ && \
    python3.6 -m compileall -b ./ && \
    find ./ -name '*.py' -exec rm '{}' ';'


FROM python:3.6-slim-stretch
ARG VERSION
ARG VCS_REF
ARG BUILD_DATE
LABEL org.label-schema.vendor="Grafolean" \
      org.label-schema.url="https://grafolean.com/" \
      org.label-schema.name="Grafolean Ping Collector" \
      org.label-schema.description="Ping collector for Grafolean" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-url="https://gitlab.com/grafolean/grafolean-collector-ping/" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.docker.schema-version="1.0"
COPY --from=python-requirements /requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
COPY --from=build-backend /pingcollector/ /pingcollector/
WORKDIR /pingcollector
USER root
CMD ["python", "-m", "pingcollector"]
