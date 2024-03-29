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
    - <code>WebService.findBestWeekPlan()</code>: core algorithm that tries to determine an optimized driving plan. Shuffles the list of persons, as their order has a big impact on the results.
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
- <code>MasterPlan.coreAlgorithm()</code>
- <code>MasterPlan.addPartiesForLazyDrivers()</code>: Fill add drives for lazy drivers while trying to optimize:
    - A/B week symetry
    - additional parties on days where it's tight
- <code>MasterPlan.balancePassengersInCars()</code>: Once we've done everything we can to make sure, no one drives more often than needed it's time to balance the passengers in the different cars. The core algorithm doesn't care about that.



sdf

# Overview of packages
