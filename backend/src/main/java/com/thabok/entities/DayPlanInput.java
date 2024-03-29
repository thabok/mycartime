package com.thabok.entities;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class DayPlanInput {

	public Map<Integer, List<Person>> personsByFirstLesson;
	public Map<Integer, List<Person>> personsByFirstLessonWithTolerance;
	public Map<Integer, List<Person>> personsByLastLesson;
	public Map<Integer, List<Person>> personsByLastLessonWithTolerance;
	public Set<Person> designatedDrivers;
	public Set<Person>  mirrorDrivers = new HashSet<>();
	
}
