package com.thabok.entities;

import java.util.List;
import java.util.Map;
import java.util.Set;

public class DayPlanInput {

	public Map<Integer, List<Person>> personsByFirstLesson;
	public Map<Integer, List<Person>> personsByLastLesson;
	public Set<Person> designatedDrivers;
	
}
