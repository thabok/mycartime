package com.thabok.entities;
public class Person {

	public String firstName;
	public String lastName;
	public String initials;
    public boolean isTall;
    public boolean isPartTime;
    public boolean isCarRoomy;
    public int numberOfSeats;
    public Schedule schedule;

    public String getName() {
    	return firstName + " " + lastName;
    }

    public int getNoPassengerSeats() {
    	return numberOfSeats - 1;
    }
    
    public String toString() {
		return getName() + "(" + initials + ")";
    }
    
    /**
     * Returns the one-based lesson number that depends on the dayOfTheWeekABCombo and whether it's the way there or back.
     * 
     * @param dayOfWeekABCombo day of the week ab combo (e.g. Monday-A)
     * @param isWayBack true if way back, false otherwise
     * @return one-based number of the first or last lesson (depends on wayThere/wayBack)
     */
    public int getLesson(DayOfWeekABCombo dayOfWeekABCombo, boolean isWayBack) {
    	if (isWayBack) {
    		return schedule.getTimingInfoPerDay().get(dayOfWeekABCombo.getUniqueNumber()).getLastLesson();
    	} else {
    		return schedule.getTimingInfoPerDay().get(dayOfWeekABCombo.getUniqueNumber()).getFirstLesson();
    	}
    }
}