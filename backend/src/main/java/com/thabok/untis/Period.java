package com.thabok.untis;

import java.util.List;

import com.thabok.entities.Teacher;

public class Period {

	public int date;
	public int startTime;
	public int endTime;
	
	/**
	 * This attribute seems to be set for break supervision items only. Value: "bs" (...break supervision?)
	 */
	public String lstype;
	
	/**
	 * Sometimes this attribute is present with a value of "cancelled". Should have no effect on the planning.
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
