package com.thabok.untis;

import java.util.ArrayList;
import java.util.List;

public class Period {

	public int date;
	public int startTime;
	public int endTime;
	
	public boolean isOnCallSubstitution() {
		for (Subject subject : su) {
			if (Subject.ON_CALL_SUBSTITUTION_ID == subject.id) {
				return true;
			}
		}
		return false;
	}
	
	/**
	 * This attribute lists the subjects for a period. The su with id 255 is the on-call-substitution
	 */
	public List<Subject> su = new ArrayList<>(1);
	
	/**
	 * This attribute seems to be set for break supervision items only. Value: "bs" (...break supervision?)
	 */
	public String lstype;
	
	/**
	 * Sometimes this attribute is present with a value of "cancelled". Should have no effect on the planning.
	 * 
	 * Code "irregular" seems to be used for class trips, etc.
	 */
	public String code;
	
	/**
	 * This attribute seems to be set for actual lesson items only. Value: "Unterricht"
	 */
	public String activityType;
	
	/**
	 * List of teachers
	 */
	public List<Teacher> te;
	
	public String toString() {
		return "[" + date + ": " + startTime + " - " + endTime + "]";
	}
	
}
