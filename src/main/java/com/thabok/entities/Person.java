package com.thabok.entities;
public class Person {

	private String name;
	private String initials;
    private boolean isTall;
    private boolean isPartTime;
    private Car car;
    private Schedule schedule;

    public Person(String name) {
		this.name = name;
	}

	public Person() {
	}

	public void setName(String name) {
        this.name = name;
    }

    public void setCar(Car car) {
        this.car = car;
    }

    public Car getCar() {
        return this.car;
    }

    public String getName() {
        return this.name;
    }

    public void setSchedule(Schedule schedule) {
        this.schedule = schedule;
    }

    public Schedule getSchedule() {
        return this.schedule;
    }
    
    public boolean isTall() {
		return isTall;
	}

	public void setTall(boolean isTall) {
		this.isTall = isTall;
	}

	public boolean isPartTime() {
		return isPartTime;
	}

	public void setPartTime(boolean isPartTime) {
		this.isPartTime = isPartTime;
	}

	public String toString() {
		return name;
	}

	public String getInitials() {
		return initials;
	}

	public void setInitials(String initials) {
		this.initials = initials;
	}

}