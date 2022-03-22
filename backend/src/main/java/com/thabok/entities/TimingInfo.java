package com.thabok.entities;

public class TimingInfo {

	private int startTime;
	private int endTime;
	
	private boolean hasDutyBeforeFirstLesson;
	private boolean hasDutyAfterLastLesson;
	
	public boolean isHasDutyBeforeFirstLesson() {
		return hasDutyBeforeFirstLesson;
	}
	public void setHasDutyBeforeFirstLesson(boolean hasDutyBeforeFirstLesson) {
		this.hasDutyBeforeFirstLesson = hasDutyBeforeFirstLesson;
	}
	public boolean isHasDutyAfterLastLesson() {
		return hasDutyAfterLastLesson;
	}
	public void setHasDutyAfterLastLesson(boolean hasDutyAfterLastLesson) {
		this.hasDutyAfterLastLesson = hasDutyAfterLastLesson;
	}
	public int getStartTime() {
		return startTime;
	}
	public void setStartTime(int startTime) {
		this.startTime = startTime;
	}
	public int getEndTime() {
		return endTime;
	}
	public void setEndTime(int endTime) {
		this.endTime = endTime;
	}
	
	
}
