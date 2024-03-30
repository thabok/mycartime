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
    public int maxDrives;
    public Map<Integer, TimingInfo> schedule = new HashMap<>();

    /**
     * Integer keys from 0-9 indicate days from Monday-A thru Friday-B.
     * The Boolean value says if the person should be considered as a designated driver on this day.  
     */
    private Map<Integer, CustomDay> customDays = Util.initializeEmptyCustomDays();
    
    public void clearCustomDays() {
    	this.customDays = null;
    }
    
    public CustomDay getCustomPrefsForCombo(DayOfWeekABCombo combo) {
    	int customDaysIndex;
		if (combo.getUniqueNumber() <= 5) {
			customDaysIndex = combo.getUniqueNumber() - 1;
		} else {
			customDaysIndex = combo.getUniqueNumber() - 3;
		}
		CustomDay customDayInfo = this.customDays.get(customDaysIndex);
		return customDayInfo;
    }

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

	public CustomDay accessCustomDaysWithCalculatedIndex(int customDayIndex) {
		return this.customDays.get(customDayIndex);
	}
}