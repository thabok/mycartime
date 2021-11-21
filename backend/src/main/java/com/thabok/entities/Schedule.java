package com.thabok.entities;
import java.util.HashMap;
import java.util.Map;

public class Schedule {

	private Map<Integer, TimingInfo> timingInfoPerDay = new HashMap<>();

	public Map<Integer, TimingInfo> getTimingInfoPerDay() {
		return timingInfoPerDay;
	}

	public void setTimingInfoPerDay(Map<Integer, TimingInfo> timingInfoPerDay) {
		this.timingInfoPerDay = timingInfoPerDay;
	}
	
}

