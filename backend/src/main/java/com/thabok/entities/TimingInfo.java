package com.thabok.entities;

public class TimingInfo {

	private int firstLesson;
	private int lastLesson;
	
	private boolean hasDutyBeforeFirstLesson;
	private boolean hasDutyAfterLastLesson;
	
	public int getFirstLesson() {
		return firstLesson;
	}
	public void setFirstLesson(int firstLesson) {
		this.firstLesson = firstLesson;
	}
	public int getLastLesson() {
		return lastLesson;
	}
	public void setLastLesson(int lastLesson) {
		this.lastLesson = lastLesson;
	}
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
	
	
}
