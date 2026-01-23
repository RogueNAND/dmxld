#!/bin/bash
set -e

case "${1:-}" in
    shell)
        exec /bin/bash
        ;;
    demo)
        shift
        exec python3 -m fcld.cli demo-basic "$@"
        ;;
    serve)
        shift
        exec python3 -m fcld.cli serve "$@"
        ;;
    run)
        shift
        SHOW_FILE="${1:-}"
        if [[ -z "$SHOW_FILE" ]]; then
            echo "Usage: run <show_file.py> [args...]"
            exit 1
        fi
        shift
        exec python3 "/app/shows/${SHOW_FILE}" "$@"
        ;;
    python)
        shift
        exec python3 "$@"
        ;;
    --help|"")
        cat <<EOF
FCLD Container

Usage:
  docker run fcld <command> [args...]

Commands:
  serve [options]        Run HTTP server (default)
  demo [--start-at N]    Run the basic demo show
  run <file.py> [args]   Run a show from /app/shows/
  python [args]          Run Python interpreter
  shell                  Start bash shell

Serve options:
  --host HOST            Host to bind to (default: 0.0.0.0)
  --port PORT            Port to listen on (default: 8080)
  --shows-dir DIR        Shows directory (default: /app/shows)

Volumes:
  /app/shows             Mount your show files here

Environment:
  OLA_HOST               OLA daemon host (default: host.docker.internal)
  OLA_PORT               OLA daemon port (default: 9010)

Examples:
  # Run HTTP server
  docker run --rm -p 8080:8080 fcld serve

  # Run demo (OLA on host machine)
  docker run --rm fcld demo

  # Run with custom shows
  docker run --rm -v ./my_shows:/app/shows fcld run my_show.py

  # Connect to OLA on specific host
  docker run --rm -e OLA_HOST=192.168.1.100 fcld demo

  # Host network mode (Linux)
  docker run --rm --network host -e OLA_HOST=127.0.0.1 fcld serve

Note: OLA daemon (olad) must be running on the host machine.
      Install: sudo apt-get install ola && olad -l 3
EOF
        ;;
    *)
        exec "$@"
        ;;
esac
