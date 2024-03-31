package com.thabok.entities;

import java.util.HashSet;
import java.util.Set;

public class PartyTuple {

	private Party schoolboundParty;
	private Party homeboundParty;
	private boolean isDesignatedDriver;
	private boolean drivesDespiteCustomPrefs;
	
	/**
	 * This list contains all persons that have the same schedule as the driver for this day.
	 */
	private Set<Person> possibleDrivers = new HashSet<>();
	
	public Person getDriver() {
		if (schoolboundParty != null) {
			return schoolboundParty.getDriver();
		} else if (homeboundParty != null) {
			return homeboundParty.getDriver();
		} else {
			return null;
		}
	}
	
	public void setSchoolboundParty(Party partyThere) throws Exception {
		if (this.getDriver() != null && this.getDriver() != partyThere.getDriver()) {
			throw new Exception("You cannot add a party with another driver to this tuple!");
		}
		this.schoolboundParty = partyThere;
	}
	
	public void setHomeboundParty(Party partyBack) throws Exception {
		if (this.getDriver() != null && this.getDriver() != partyBack.getDriver()) {
			throw new Exception("You cannot add a party with another driver to this tuple!");
		}
		this.homeboundParty = partyBack;
	}
	
	public Party getSchoolboundParty() {
		return schoolboundParty;
	}
	
	public Party getHomeboundParty() {
		return homeboundParty;
	}
	
	public String toString() {
		return schoolboundParty.toString() + "\n" + homeboundParty.toString();
	}

	public Set<Person> getPossibleDrivers() {
		return possibleDrivers;
	}

	public void setPossibleDrivers(Set<Person> possibleDrivers) {
		this.possibleDrivers = possibleDrivers;
	}
	
	public void addPossibleDriver(Person possibleDriver) {
		this.possibleDrivers.add(possibleDriver);
	}

	public boolean isDesignatedDriver() {
		return isDesignatedDriver;
	}

	public void setDesignatedDriver(boolean isDesignatedDriver) {
		this.isDesignatedDriver = isDesignatedDriver;
	}

	public boolean isDrivesDespiteCustomPrefs() {
		return drivesDespiteCustomPrefs;
	}

	public void setDrivesDespiteCustomPrefs(boolean drivesDespiteCustomPrefs) {
		this.drivesDespiteCustomPrefs = drivesDespiteCustomPrefs;
	}
	
}
