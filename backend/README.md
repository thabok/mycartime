# Main entry point
- The main function in <code>Main.java</code> starts <code>WebService</code>
- The <code>WebService</code> provides the following endpoints on port 1337 that are used by the frontend:
    - <code>GET</code> -> <code>/check</code>: returns true (allows to check if the service is available)
    - <code>POST</code> -> <code>/login</code>: uses the credentials to authenticate with the WebUntis server and returns the sessionId.
    - <code>POST</code> -> <code>/logout</code>: performs a logout (required by the WebUntis server to allow future logins without a time penalty)
    - <code>POST</code> -> <code>/checkConnection</code>: performs a login with the given credentials and (if the login was successful) perorms a logout
    - <code>POST</code> -> <code>/calculatePlan</code>: Core function that starts the calculation of a new driving plan based on the given configuration (people, their custom preferences, start date)
    - <code>GET</code> -> <code>/progress</code>: returns the progress of the running driving plan calculations

- Additionally, the <code>WebService</code> logs all incoming requests (except progress polls) and has CORS enabled by default.


# Main Control Flow
Assumes that the WebService is running (Main function -> WebService)

- Frontend calls <code>/login</code>
- Frontend calls <code>/calculatePlan</code> -> <code>WebService.calculatePlan()</code>
    - for each person:
        - <code>WebService.updateProgress(...)</code>
        - <code>WebService.getTimetable(person, startDate)</code>: queries the person's timetable from the WebUntis server
        - <code>TimetableHelper.timetableToSchedule(...)</code>: transforms the WebUntis data into something more usable
    - <code>WebService.findBestWeekPlan()</code>: core algorithm that tries to determine an optimized driving plan. Shuffles the list of persons and weekday-ab-combos, as their order has a big impact on the results.
    - <code>Controller.calculateWeekPlan()</code>: performs the driving plan calculation once more while using a fixed order of persons. This allows enhanced logging and retracing of the steps taken. Cannot happen in the main algorithm's improvement loop, because the quality the iteration results is evaluated at a later point in time.
    - <code>WebService.storePersonsTimesPerDayPlan()</code>: stores each persons individual arrival/departure times in the respective day plans. This is required because we later remove most data of each person (incl. the schedule) to prevent data explosion because of nested references that are explicitly serialized.
    - <code>PlanOptimizationHelper.printTightnessOverview()</code>: introduced to have feedback on solutions or issue #11
    - <code>WebService.clearDataFromPlan()</code>: Removes most data of each person (incl. the schedule) to prevent data explosion because of nested references that are explicitly serialized.
- Frontend calls <code>/logout</code>

## Control Flow of WebService.findBestWeekPlan()
Core algorithm that tries to determine an optimized driving plan. Shuffles the list of persons and week days, as their order has a big impact on the results. Measures a plans fitness based on the following factors:

1. minimizing the number of persons with more than 4 drives
2. minimizing the number of persons with more than 5 drives
3. minimizing the number of persons with involuntary drives

- <code>WebService.findBestWeekPlan()</code>: shuffle loop until specified number of iterations have yielded no improvements
    - <code>Collections.shuffle(persons)</code>
    - <code>Collections.shuffle(Util.weekdayListAB)</code>
    - <code>Controller.calculateWeekPlan(...)</code>: core algorithm to create a good plan based on the current shuffles
    - calculate current candidates fitness
    - discard current candidate if not better than the best plan so far (lower fitness value = better)
- loop stops when the specified number of iterations didn't result in a better plan

## Control Flow of Controller.calculateWeekPlan()
By default, this function is called from the optimization loop <code>WebService.findBestWeekPlan()</code> with no preset. It works based on a freshly shuffled list of persons and weekdaysAB (i.e., 10 DayOfTheWeekABCombos: Monday-A thru Friday-B).

- <code>new MasterPlan(persons, preset)</code> (constructor) -> <code>MasterPlan.initialize()</code>: for each DayOfTheWeekABCombo:
    - initializes DayPlanInput objects (persons by 1st lesson, persons by last lesson, designated drivers)
    - creates the needed day plan objects
    - adds parties for the designated drivers
- <code>AlternativeDriverHelper.findAlternativeForSirDrivesALots()</code>: If someone is already driving a lot at this point (more than 4 times), let's try to reduce that by adding a tolerance on the wayThere (merges first-lesson with people who have hall-duty before the first lesson).
- <code>MasterPlan.coreAlgorithm()</code>: Adds people to existing parties _if possible_ and create new parties _when needed_
    - Persons to be placed are sorted based on their number of total drives (desc)
    - For the creation of parties, we prefer people with a low noDrives for the resp. week, ideally already driving on the mirror day
    - The result is still slightly imbalanced, due to the nature of the approach
    - Also the passengers need to be rebalanced (there may be to parties at the same time with one full car and one pretty empty car)
- <code>MasterPlan.addPartiesForLazyDrivers()</code>: Fill add drives for lazy drivers while trying to optimize:
    - A/B week symetry
    - additional parties on days where it's tight
- <code>MasterPlan.balancePassengersInCars()</code>: Once we've done everything we can to make sure, no one drives more often than needed it's time to balance the passengers in the different cars. The core algorithm doesn't care about that.
- Some summary prints to the console (only visible for the trace-run of the final plan)
    - <code>Util.printDrivingDaysAbMap()</code>
    - <code>Util.summarizeNumberOfDrives()</code>


# Overview of packages
- main
    - <code>Main.java</code> main function, starts WebService.java
    - <code>Controller.java</code> core algorithm
- entities
    - <code>PlanInputData</code>: Wrapper for the data coming from the frontend (POST /calculatePlan)
    - <code>CustomDay</code>: Custom Preferences that are configured by the user (frontend)
    - <code>DayOfWeekABCombo</code>: Combo of a weekday (Mon-Fri) and a week number (A-B)
    - <code>DayPlan</code>: Contains carpool parties and additional information for 1 day of the 10-day plan
    - <code>DayPlanInput</code>: For a given day: Maps persons by 1st/last lesson, with and without tolerances and lists the designated drivers
    - <code>MasterPlan</code>: Main data object for the week plan (10-day plan) that is produced and optimized
    - <code>NumberOfDrivesStatus</code>: Helper class to facilitate queries regarding the number of drives of a person in a given plan
    - <code>Party</code>: a party (schoolbound or homebound) consists of 1 driver (Person) and a list of passengers (also Persons)
    - <code>PartyTuple</code>: the schoolbound and homebound parties of 1 driver are combined as a party tuple
    - <code>Person</code>: a person with name, initials, schedule, etc.
    - <code>ProgressObject</code>: Wrapper for progress value & message
    - <code>TimingInfo</code>:  
    - <code>Schedule</code>: Maps a TimingInfo object to each of the 10 days
    - <code>Reason</code>: Enumeration describing the reason for the existance of a party (to help understand the choices of the algorithm)
- untis
    - <code>WebUntisAdapter</code>: main class for any interaction with WebUntis (with hardcoded schoolname and webuntis-server-url)
    - <code>TimetableWrapper</code>: wrapper for the WebUntis server response when querying a timetable
    - <code>Subject</code>: wrapper class for a subject
    - <code>Teacher</code>: wrapper class for a teacher
    - <code>Period</code>: a Period has a date, startTime, endTime and a bunch of meta data (incl. a list of teachers)
- helper
    - AlternativeDriverHelper
    - ControllerInitHelper
    - PartyHelper
    - PlanOptimizationHelper
    - TimetableHelper
- util
    - Constants
    - JsonUtil
    - Util
- webservice