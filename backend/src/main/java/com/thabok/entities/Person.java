package com.thabok.entities;
public class Person {

	public String firstName;
	public String lastName;
	public String initials;
    public boolean isTall;
    public boolean isPartTime;
    public boolean isCarRoomy;
    public int numberOfSeats;
    public Schedule schedule;

    public String getName() {
    	return firstName + " " + lastName;
    }

    public int getNoPassengerSeats() {
    	return numberOfSeats - 1;
    }
    
    public String toString() {
		return getName() + "(" + initials + ")";
    }
    
}