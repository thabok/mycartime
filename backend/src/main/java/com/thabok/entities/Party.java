package com.thabok.entities;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.thabok.util.Util;

public class Party {

	private DayOfWeekABCombo dayOfWeekABCombo;
	private boolean isWayBack;
	private Person driver;
	private int time;
	private List<Person> passengers = new ArrayList<>();
	private Map<String, String> reasonPhrasesByInitials = new HashMap<>();
	private String reasonForParty;

	public Party(String reasonPhrase) {
		reasonForParty = reasonPhrase;
	}

	public Person getDriver() {
		return driver;
	}

	public int getTime() {
		return time;
	}

	public void setTime(int time) {
		this.time = time;
	}

	public void setDriver(Person driver) {
		this.driver = driver;
	}

	public List<Person> getPassengers() {
		return passengers;
	}
	
	public Person popPassenger() {
		if (!passengers.isEmpty()) {
			Person removedPassenger = passengers.remove(passengers.size() - 1);
			updateTime();
			return removedPassenger;
		}
		throw new IllegalStateException("Cannot remove passengers because... there are none.");
	}

	/**
	 * Updates the party time to the earliest time (if wayThere) or the latest time (if wayBack) of any member (driver/passengers).
	 */
	private void updateTime() {
		int updatedTime;
		if (this.isWayBack) {
			updatedTime = driver.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getEndTime();
			for (Person passenger : this.passengers) {
				int passengerTime = passenger.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getEndTime();
				updatedTime = Math.max(updatedTime, passengerTime);
			}
		} else {
			updatedTime = driver.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getStartTime();
			for (Person passenger : this.passengers) {
				int passengerTime = passenger.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getStartTime();
				updatedTime = Math.min(updatedTime, passengerTime);
			}
		}
		this.time = updatedTime;
		
	}

	/**
	 * Sets passengers. If this list contains the driver he will be ignored
	 * @param passengers
	 * @throws Exception if you try to add too many people
	 */
	public void setPassengers(List<Person> passengers) throws Exception {
		this.passengers = passengers;
		try {
			if (this.passengers.contains(driver)) {
				this.passengers.remove(driver);
			}
		} catch (Exception e) {
		}
		this.updateTime();
	}
	
	/**
	 * Adds the passenger to the party and adapts the parties time if needed (can happen due to supervisions).
	 * 
	 * @param p the passenger to add to the party
	 * @param reasonPhrase explains why the passenger is added to this party
	 */
	public void addPassenger(Person p, String reasonPhrase) {
		if (passengers.size() >= driver.getNoPassengerSeats()) {
			throw new IllegalStateException("Cannot add a passenger to " + driver + "'s car, it's already full!");
		}
		this.passengers.add(p);
		this.reasonPhrasesByInitials.put(p.initials, reasonPhrase);
		this.updateTime();
	}

	public DayOfWeekABCombo getDayOfTheWeekABCombo() {
		return dayOfWeekABCombo;
	}

	public void setDayOfTheWeekABCombo(DayOfWeekABCombo dayOfWeekABCombo) {
		this.dayOfWeekABCombo = dayOfWeekABCombo;
	}

	public boolean isWayBack() {
		return isWayBack;
	}

	public void setWayBack(boolean isWayBack) {
		this.isWayBack = isWayBack;
	}

	public String toString() {
		return (isWayBack ? "[<-] " : "[->] ")
				+ "[" + getTimeAsString() +  "] "
				+ driver.getName()
				+ (passengers.isEmpty() ? "" : " (" + String.join(", ", passengers.stream().map(p -> p.getName()).collect(Collectors.toList())) + ")");
	}
	
	public int getNumberOfFreeSeats() {
		if (driver == null) {
			throw new IllegalStateException("Cannot query free seats for a party without a driver. Was it properly initialized?!");
		}
		return driver.getNoPassengerSeats() - passengers.size();
	}
	
	public boolean hasAFreeSeat() {
		return getNumberOfFreeSeats() > 0;
	}

	public String getTimeAsString() {
		return Util.getTimeAsString(time);
	}

	public void removePassenger(Person personToRemove) {
		this.passengers.remove(personToRemove);
		this.reasonPhrasesByInitials.remove(personToRemove.initials);
		updateTime();
	}

	public List<Person> removePassengers() {
		List<Person> removedPassengers = this.passengers;
		this.passengers = new ArrayList<>();
		return removedPassengers;
	}

	public String getReasonForParty() {
		return reasonForParty;
	}
}
