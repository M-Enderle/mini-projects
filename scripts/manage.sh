#!/bin/bash

# Management script for mini-projects
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to show usage
show_usage() {
    print_color $BLUE "Mini Projects Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start [service]    - Start all services or specific service"
    echo "  stop [service]     - Stop all services or specific service"
    echo "  restart [service]  - Restart all services or specific service"
    echo "  logs [service]     - Show logs for all services or specific service"
    echo "  build [service]    - Build all services or specific service"
    echo "  status             - Show status of all services"
    echo "  add <name> [type]  - Add new project (calls add-project.sh)"
    echo "  list               - List all projects"
    echo "  clean              - Clean up unused Docker resources"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 start kleinanzeigen-map  # Start specific service"
    echo "  $0 logs -f                  # Follow logs for all services"
    echo "  $0 add my-api fastapi       # Add new FastAPI project"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yaml" ]; then
    print_color $RED "Error: Must be run from the mini-projects root directory"
    exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

COMMAND=$1
shift

case $COMMAND in
    start)
        if [ $# -eq 0 ]; then
            print_color $GREEN "Starting all services..."
            docker-compose up -d
        else
            SERVICE=$1
            print_color $GREEN "Starting service: $SERVICE"
            docker-compose up -d "$SERVICE"
        fi
        ;;
    
    stop)
        if [ $# -eq 0 ]; then
            print_color $YELLOW "Stopping all services..."
            docker-compose down
        else
            SERVICE=$1
            print_color $YELLOW "Stopping service: $SERVICE"
            docker-compose stop "$SERVICE"
        fi
        ;;
    
    restart)
        if [ $# -eq 0 ]; then
            print_color $YELLOW "Restarting all services..."
            docker-compose restart
        else
            SERVICE=$1
            print_color $YELLOW "Restarting service: $SERVICE"
            docker-compose restart "$SERVICE"
        fi
        ;;
    
    logs)
        if [ $# -eq 0 ]; then
            print_color $BLUE "Showing logs for all services..."
            docker-compose logs -f
        else
            # Check if first argument is a flag
            if [[ $1 == -* ]]; then
                print_color $BLUE "Showing logs for all services..."
                docker-compose logs "$@"
            else
                SERVICE=$1
                shift
                print_color $BLUE "Showing logs for service: $SERVICE"
                docker-compose logs "$@" "$SERVICE"
            fi
        fi
        ;;
    
    build)
        if [ $# -eq 0 ]; then
            print_color $GREEN "Building all services..."
            docker-compose build
        else
            SERVICE=$1
            print_color $GREEN "Building service: $SERVICE"
            docker-compose build "$SERVICE"
        fi
        ;;
    
    status)
        print_color $BLUE "Service status:"
        docker-compose ps
        echo ""
        print_color $BLUE "Resource usage:"
        docker stats --no-stream
        ;;
    
    add)
        if [ $# -lt 1 ]; then
            print_color $RED "Error: Project name required"
            echo "Usage: $0 add <project-name> [project-type]"
            exit 1
        fi
        PROJECT_NAME=$1
        PROJECT_TYPE=${2:-streamlit}
        print_color $GREEN "Adding new project: $PROJECT_NAME ($PROJECT_TYPE)"
        ./scripts/add-project.sh "$PROJECT_NAME" "$PROJECT_TYPE"
        ;;
    
    list)
        print_color $BLUE "Current projects:"
        echo ""
        # List directories that have Dockerfile
        for dir in */; do
            if [ -f "${dir}Dockerfile" ]; then
                PROJECT_NAME=${dir%/}
                if [ -f "${dir}pyproject.toml" ]; then
                    # Extract description from pyproject.toml if available
                    DESCRIPTION=$(grep '^description' "${dir}pyproject.toml" | cut -d'"' -f2 2>/dev/null || echo "No description")
                    print_color $GREEN "  📁 $PROJECT_NAME - $DESCRIPTION"
                else
                    print_color $GREEN "  📁 $PROJECT_NAME"
                fi
            fi
        done
        echo ""
        print_color $BLUE "Available at: http://projects.enderles.com/"
        ;;
    
    clean)
        print_color $YELLOW "Cleaning up Docker resources..."
        docker system prune -f
        docker image prune -f
        print_color $GREEN "Cleanup complete"
        ;;
    
    *)
        print_color $RED "Error: Unknown command '$COMMAND'"
        show_usage
        exit 1
        ;;
esac 