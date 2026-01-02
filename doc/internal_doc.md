# Carpool Party
An application for teachers that plans carpool parties based on their schedules. 

## System Scope
The application consists of the following modules:

### User Interface (web app)
1. Timetable Provider Authentication
2. Member Configuration and Custom Settings
3. Driving Plan Viewer and Editor

### Backend (python)
1. Request Broker (handles connection from the frontend)
2. Timetable Provider Connector (queries the timetables of all members)
3. Core algorithm (receives list of persons, queries their timetables and calculates the driving plan that consists of 10 day plans (MON-FRI in week A + MON-FRI in week B)


## Algorithm
This section outlines the core algorithm used to create the driving plan. Ideas, concepts, requirements and constraints are described here.

### Requirements and Constraints
The goal is to create a driving plan across a 2-week “week-A; week-B” cycle with parties for each day. 
1. “No one gets left behind”:
    * For each day, the plan must ensure that all relevant participants are accounted for:
    * the plan must provide enough drivers so that the assigned passengers + the driver fit in the drivers car (number of passengers + 1 <= number of seats)
2. The passengers that ride with a driver can be different on the school bound journey and the home bound journey but the same person cannot be both driver and passenger on the same day.
3. Over the 2-week cycle the plan shall optimise for the following factors 
    1. Limit maximum number of drives across the 2-week-cycle
        * A full time person shall drive 4 times (ideally twice per week).
        * A part time person (e.g. teacher in training) shall drive 2 times (ideally once per week). 
        * These numbers shall only be exceeded if 
            * [SINGLE BAD SCHEDULE] a person’s schedule doesn’t allow a better plan (e.g. if someone’s schedule has more than 4 days on which they must drive because nobody else shares their arrival or departure times) or
            * [GLOBAL BAD SCHEDULE] if the complete plan doesn’t work out otherwise
        * in the case of [GLOBAL BAD SCHEDULE], the algorithm shall report the critical set of persons out of which one or more have to drive more than 4 times across the 2 weeks. The algorithm shall accept a sorted list of persons to prefer for this choice (e.g., if it has to hit someone, is should hit Joe))
    2. Try to keep the number of passengers in a car below the maximum whenever possible
        * This should never increase anybody’s number of drives over the defined maximum
        * Most of the time, after creating the parties required to ensure everyone gets to school and back on all days, there are still multiple people with driving capacity that can create additional parties to reduce the pressure on a tight day
        * Apart from “Mandatory Drivers” (people who have to drive -> no choice because the arrive/leave at a time where nobody else arrives/leaves) the choice of a driver for a given day always impacts the remaining choices on all days. This is important because “bad choices” can lead to sticky situations where no acceptable plan can be created
    3. Tolerances: don’t be strict with start and end times:
        * A tolerance in minutes (default: 30 minutes) describes the maximum deviation between different members to accept them for the same time slot.
        * Party Time Convenience: Since a party must comply with the “worst” time of all members (i.e. the earliest arrival time on the way to school / the latest leaving time on the way back), try to keep people together, who have special times due to hall and yard supervision duties, etc.
            * Example 1:
                * Two drivers, both need to arrive at school at 7:55h (normal starting time for the first lesson)
                * 5 persons that need to be placed into parties, 2 of them need to be there early (7:40h), the rest at 7:55h
                * The two persons shall be placed into the same party and the others shall be placed into another party, so they are not unnecessarily bothered by this.
            * Example 2:
                * Two drivers, one needs to arrive at school at 7:55h, one at 7:40h 
                * 6 persons that need to be placed into parties, 1 of them needs to be there early (7:40h), the rest at 7:55h
                * The 1 early person shall be placed into the same party as the early driver. As the remaining 5 persons don’t fit into the 7:55h-party, one of the passengers is unlucky and also gets placed into the early party (7:40h). The other 4 are lucky and ride with the 7:55-driver.
            * Party time convenience has a higher priority than the goal to try and keep parties below the maximum capacity of a car

### Driver Candidate Pools
To create an optimal driving plan, the algorithm uses the concept of **Driver Candidate Pools** for the required time slots of each day. A pool contains all members who are eligible to drive on that specific slot, considering factors such as:
* Their availability based on their timetable and custom settings
* Their remaining driving capacity within the 2-week cycle

The algorithm first creates Parties for all pools with size 1, assigning those members as drivers for the respective time slots across all days. It then iteratively considers larger pools, selecting drivers based on their remaining capacity and the overall optimization goals. The pools of size 1 are known as **Mandatory Drivers**. 

For pools of size greater than 1, the algorithm must find an intelligent way to select drivers that balances the load across all members while adhering to the defined constraints and optimization goals. This involves evaluating the impact of each potential driver selection on the overall plan and making choices that lead to the most efficient and fair distribution of driving duties.

## User Interface

The app is a carpool planner for teachers that creates suitable carpool parties based on their schedules. To create a new plan, the user needs to provide username and password, which are used by a backend service to query the schedules (the basis for the plan). Working on an existing plan or loading a plan from a JSON file does not require authentication.

The main space of the app shall be available to allow the user to configure the
carpool members (import/export json or manually add/edit/delete members) and to review and fine tune the driving plan once it has been generated or loaded (json file). 

Reference date selection: the driving plan is created for a 2-week cycle (week A + week B). To determine which weeks these are, the user shall be able to select a reference date (Monday of week A).

Member configuration:
- List of members (card view/list view, searchable)
- For each member:
    - Name
    - Initials
    - Is Part Time (boolean)
    - Number of seats
    - Custom preferences
Schema: `schema/members.json`

When the user has entered username and password, a reference date has been picked (and it's a Monday) and there is at least one member and no plan is currently, a button to generate a driving plan shall become active. It shall POST to 127.0.0.1:1338/api/v1/drivingplan with the a payload as defined in driving_plan_request.json.

Driving plan editor:
- Summary of current plan
- Details view (filters to focus on a certain person, week a / week b or both)
- Edit dialog for a day plan to move passengers from one party to another

For an existing plan, the app shall provide an option to save the plan to a JSON file and to a PDF (using a backend service) and to discard the plan (enabling the creation of a new plan). 
Driving plan schema: `schema/driving_plan.json`

The plan and the member configuration shall be saved to local storage automatically so that the user can continue working on it later without losing data.

## API description

### Backend - REST API Endpoints
The backend exposes a REST API with the following endpoints:
* `GET /api/v1/check`: Checks the connection to the backend
* `POST /api/v1/drivingplan`: Calculates a driving plan based on the provided member data

The `drivingplan` endpoint expects a JSON payload defined by the schema in `schemas/driving_plan_request.json` and returns a response defined by the schema in `schemas/driving_plan.json`.

### Frontend - File formats for loading and saving data
The frontend uses JSON files to load and save member configurations and driving plans. The file formats are defined by the schemas in `schemas/members.json` and `schemas/driving_plan.json`.


## Glossary
* **Member, Carpool Party Member, Person**: A teacher who participates in the carpool group and who has an account with the timetable provider
* **Driver**: A person who drives on a given day
* **Passenger**: A person who rides with someone else on a given day
* **Mandatory Driver**: A person who must be a driver on a given day, because they arrive at school or leave school at a time where nobody else arrives / leaves
* **Party**: A group of people, driver + passengers (optional) for a specified day, time and direction 
* **Timetable Provider**: External service that can be queried to retrieve the timetables for a teacher
* **Timetable**: A list of periods for a specified range of days. The essential information from this is the required start-of-duty time and the end-of-duty time for each day.
* **Custom Day, Custom Preferences**: Customised data that overrides the schedule. Can define a custom start time, end time and several other settings.
