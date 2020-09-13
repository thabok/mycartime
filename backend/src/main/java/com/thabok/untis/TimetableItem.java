package com.thabok.untis;

public class TimetableItem {

	public int date;
	public int startTime;
	public int endTime;
	
	public String toString() {
		return "[" + date + ": " + startTime + " - " + endTime + "]";
	}
	
}
