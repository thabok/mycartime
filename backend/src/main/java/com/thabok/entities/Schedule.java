package com.thabok.entities;
import java.time.DayOfWeek;
import java.util.HashMap;
import java.util.Map;

public class Schedule {

	private Map<DayOfWeek, TimingInfo> timingInfoPerDay = new HashMap<>();

	public Map<DayOfWeek, TimingInfo> getTimingInfoPerDay() {
		return timingInfoPerDay;
	}

	public void setTimingInfoPerDay(Map<DayOfWeek, TimingInfo> timingInfoPerDay) {
		this.timingInfoPerDay = timingInfoPerDay;
	}
	
	
}

