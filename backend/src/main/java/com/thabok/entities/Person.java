package com.thabok.entities;

import java.util.HashMap;
import java.util.Map;

import com.thabok.util.Util;

public class Person {

	public String firstName;
	public String lastName;
	public String initials;
    public boolean isTall;
    public boolean isPartTime;
    public boolean isCarRoomy;
    public int numberOfSeats;
    public Map<Integer, TimingInfo> schedule = new HashMap<>();

    /**
     * Integer keys from 0-9 indicate days from Monday-A thru Friday-B.
     * The Boolean value says if the person should be considered as a designated driver on this day.  
     */
    public Map<Integer, CustomDay> customDays = Util.initializeEmptyCustomDays();
    

    public String getName() {
    	return firstName + " " + lastName;
    }

    public int getNoPassengerSeats() {
    	return numberOfSeats - 1;
    }
    
    public String toString() {
		return firstName + " (" + initials + ")";
    }
    
    /**
     * Returns the one-based lesson number that depends on the dayOfTheWeekABCombo and whether it's the way there or back.
     * <br><br>
     * <b>ONLY CALL IF YOU'RE SURE THE PERSON IS ACTIVE FOR THAT DAY!</b>
     * 
     * @param dayOfWeekABCombo day of the week ab combo (e.g. Monday-A)
     * @param isWayBack true if way back, false otherwise
     * @return one-based number of the first or last lesson (depends on wayThere/wayBack)
     */
    public int getTimeForDowCombo(DayOfWeekABCombo dayOfWeekABCombo, boolean isWayBack) {
    	if (isWayBack) {
    		return schedule.get(dayOfWeekABCombo.getUniqueNumber()).getEndTime();
    	} else {
    		return schedule.get(dayOfWeekABCombo.getUniqueNumber()).getStartTime();
    	}
    }
}